import base64
import random
from os import path
import logging
import threading
import subprocess

import pyroute2
import docker

CHALLENGE_FOLDER = './challenges'
COMPOSE_CMD = 'docker-compose'

class ManagerException(Exception):
    pass

class User:
    @staticmethod
    def decode_cn(cn):
        missing_padding = len(cn) % 8
        if missing_padding != 0:
            cn += '=' * (8 - missing_padding)
        return base64.b32decode(cn.encode('utf-8')).decode('utf-8')
    @staticmethod
    def _fmt_address(address, port):
        return '{}:{}'.format(address, port)

    def __init__(self, cn, vlan, challenge):
        self.connections = set()

        self.cn = cn
        self.name = self.decode_cn(cn)
        self.vlan = vlan
        self.challenge = challenge

        self.id = '{}_{}'.format(cn.lower(), self.challenge.name)
        self.lock = threading.RLock()

    def _get_compose_cmd(self, *args):
        command = [ COMPOSE_CMD, '--project-name', self.id ]
        for conf in self.challenge.compose_files:
            command.extend([ '--file', path.normpath(path.join(CHALLENGE_FOLDER, conf)) ])

        command.extend(list(args))
        logging.debug(' '.join(command))
        return command

    def is_running(self):
        with self.lock:
            return len(subprocess.check_output(self._get_compose_cmd('top')).decode('utf-8').strip()) > 0
    def stop_compose(self, timeout=10):
        with self.lock:
            subprocess.check_call(self._get_compose_cmd('down', '--timeout', str(timeout)))
            logging.debug('cluster down for %s\'s %s challenge', self.name, self.challenge.name)

    def _get_bridge_iface(self):
        nets = self.challenge.dockerc.networks.list(names=[self.id+'_default'])
        if not nets:
            raise ValueError('No default network up for {}'.format(self.id))

        return self.challenge.ipdb.interfaces['br-'+nets[0].id[:12]]
    def _vlan_ifname(self):
        suffix = '.{}'.format(self.vlan)
        return self.challenge.host_veth.ifname[:15-len(suffix)] + suffix

    def ensure_vlan_bridged(self):
        with self.lock:
            vlan_ifname = self._vlan_ifname()
            if not vlan_ifname in self.challenge.ipdb.interfaces:
                logging.info('creating vlan %s', vlan_ifname)
                vlan_if = (self.challenge.ipdb
                        .create(kind='vlan', ifname=vlan_ifname, link=self.challenge.host_veth, vlan_id=self.vlan)
                        .commit())
            else:
                vlan_if = self.challenge.ipdb.interfaces[vlan_ifname]

            vlan_if.up().commit()

            bridge_if = self._get_bridge_iface()
            if vlan_if.master != bridge_if.index:
                logging.info('adding vlan %s to bridge %s', vlan_ifname, bridge_if.ifname)

                # Strip IP addresses from host bridge to prevent host attacks
                for addr, mask in bridge_if.ipaddr:
                    bridge_if.del_ip(addr, mask)

                (bridge_if
                    .add_port(vlan_if)
                    .commit())
    def ensure_vlan_gone(self):
        with self.lock:
            vlan_ifname = self._vlan_ifname()
            if vlan_ifname in self.challenge.ipdb.interfaces:
                logging.info('removing vlan %s', vlan_ifname)
                with self.challenge.ipdb.interfaces[vlan_ifname] as vlan_if:
                    vlan_if.remove()

    def add_connection(self, address, port):
        with self.lock:
            if len(self.connections) == 0:
                logging.info('first connection of user %s to challenge %s, booting cluster...', self.name, self.challenge.name)

                if self.is_running():
                    logging.warn('cluster for user %s\'s %s challenge is already running, stopping it now...', self.name, self.challenge.name)
                    self.stop_compose(timeout=3)

                subprocess.check_call(self._get_compose_cmd('up', '--detach'))
                logging.debug('cluster up for %s\'s %s challenge', self.name, self.challenge.name)

                self.ensure_vlan_bridged()

            address = self._fmt_address(address, port)
            logging.info('user %s connected from %s to challenge %s', self.name, address, self.challenge.name)
            self.connections.add(address)
    def remove_connection(self, address, port):
        with self.lock:
            address = self._fmt_address(address, port)
            if address not in self.connections:
                logging.warn('attempting to remove non-existent connection of user %s to challenge %s (from %s)', self.name, self.challenge.name, address)
                return

            logging.info('user %s (at %s) disconnected from challenge %s ', self.name, address, self.challenge.name)
            self.connections.remove(address)

            if len(self.connections) == 0:
                if not self.is_running():
                    logging.warn('last connection of user %s to challenge %s removed, but the cluster isn\'t running', self.name, self.challenge.name)
                    return

                logging.info('no connections remain of user %s to challenge %s, shutting cluster down...', self.name, self.challenge.name)
                self.stop_compose()
                self.ensure_vlan_gone()
    def stop(self):
        with self.lock:
            self.stop_compose(timeout=2)

class Challenge:
    def __init__(self, ipdb, dockerc, name, host_veth, compose_files):
        self.ipdb = ipdb
        self.dockerc = dockerc
        self.host_veth = ipdb.interfaces[host_veth]
        (self.host_veth
            .up()
            .commit())

        self.name = name
        self.compose_files = compose_files
        self.vlans = set()

        self.users = {}
        self.users_lock = threading.RLock()

    def _next_vlan(self):
        with self.users_lock:
            vlan = None
            while not vlan:
                p_vlan = random.randint(10, 4000)
                if p_vlan not in self.vlans:
                    vlan = p_vlan
                    self.vlans.add(vlan)

        return vlan
    def _ensure_user_exists(self, cn):
        if cn not in self.users:
            with self.users_lock:
                if cn not in self.users:
                    self.users[cn] = User(cn, self._next_vlan(), self)

    def connect_user(self, cn, address, port):
        self._ensure_user_exists(cn)

        user = self.users[cn]
        user.add_connection(address, port)
        return user.vlan
    def disconnect_user(self, cn, address, port):
        self._ensure_user_exists(cn)

        self.users[cn].remove_connection(address, port)

    def disconnect_all(self):
        with self.users_lock:
            for u in self.users:
                u.stop()

class Manager:
    def __init__(self):
        self.host_ns = pyroute2.NetNS('host')
        self.ipdb = pyroute2.IPDB(nl=self.host_ns)
        self.dockerc = docker.from_env()

        self.challenges = {}
        self.challenges_lock = threading.RLock()

    def register_challenge(self, name, host_veth, compose_files):
        with self.challenges_lock:
            if name in self.challenges:
                logging.warn('challenge %s is already registered', name)
                return

            logging.info('registering challenge %s', name)
            self.challenges[name] = Challenge(self.ipdb, self.dockerc, name, host_veth, compose_files)

    def connect_user(self, name, cn, address, port):
        return self.challenges[name].connect_user(cn, address, port)

    def disconnect_user(self, name, cn, address, port):
        self.challenges[name].disconnect_user(cn, address, port)

    def _stop(self):
        with self.challenges_lock:
            for c in self.challenges.values():
                c.disconnect_all()

            self.dockerc.close()
            self.ipdb.release()
            self.host_ns.close()
