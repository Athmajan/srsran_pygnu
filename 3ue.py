#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: 3UE_flowchart (trimmed from 5UE)
# GNU Radio version: 3.8.x

from distutils.version import StrictVersion

if __name__ == '__main__':
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print("Warning: failed to XInitThreads()")

from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import zeromq
from gnuradio.qtgui import Range, RangeWidget
from gnuradio import qtgui

class top_block(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "3UE_flowchart")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("3UE_flowchart")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except:
            pass
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "top_block")

        try:
            if StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
                self.restoreGeometry(self.settings.value("geometry").toByteArray())
            else:
                self.restoreGeometry(self.settings.value("geometry"))
        except:
            pass

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 23.04e6
        # reduced to three UE gains
        self.gain2 = gain2 = 0.06
        self.gain1 = gain1 = 0.04
        self.gain0 = gain0 = 0.05

        ##################################################
        # Blocks
        ##################################################
        # Three Range widgets for three UE gains
        self._gain0_range = Range(0.001, 0.999, 0.001, 0.05, 200)
        self._gain0_win = RangeWidget(self._gain0_range, self.set_gain0, 'gain0', "counter_slider", float)
        self.top_grid_layout.addWidget(self._gain0_win)
        
        self._gain1_range = Range(0.001, 0.999, 0.001, 0.04, 200)
        self._gain1_win = RangeWidget(self._gain1_range, self.set_gain1, 'gain1', "counter_slider", float)
        self.top_grid_layout.addWidget(self._gain1_win)
        
        self._gain2_range = Range(0.001, 0.999, 0.001, 0.06, 200)
        self._gain2_win = RangeWidget(self._gain2_range, self.set_gain2, 'gain2', "counter_slider", float)
        self.top_grid_layout.addWidget(self._gain2_win)

        
        
        # Tx Ports =============================================================
        # gNB
        self.zmq_req_gnB_tx0 = zeromq.req_source(gr.sizeof_gr_complex, 1, 'tcp://localhost:2000', 100, False, -1)
        # UE1 TX0
        self.zmq_req_ue1_tx0 = zeromq.req_source(gr.sizeof_gr_complex, 1, 'tcp://localhost:2101', 100, False, -1)
        # UE2 TX0
        self.zmq_req_ue2_tx0 = zeromq.req_source(gr.sizeof_gr_complex, 1, 'tcp://localhost:2201', 100, False, -1)
        # UE3 Tx0
        self.zmq_req_ue3_tx0 = zeromq.req_source(gr.sizeof_gr_complex, 1, 'tcp://localhost:2301', 100, False, -1)

        ## Rx Ports =============================================================
        # GnB Rx0
        self.zmq_rep_gnb_rx0 = zeromq.rep_sink(gr.sizeof_gr_complex, 1, 'tcp://*:2001', 100, False, -1)
        # UE1 Rx0
        self.zmq_rep_ue1_rx0 = zeromq.rep_sink(gr.sizeof_gr_complex, 1, 'tcp://*:2100', 100, False, -1)
        # UE2 Rx0
        self.zmq_rep_ue2_rx0 = zeromq.rep_sink(gr.sizeof_gr_complex, 1, 'tcp://*:2200', 100, False, -1)
        # UE3 Rx0
        self.zmq_rep_ue3_rx0 = zeromq.rep_sink(gr.sizeof_gr_complex, 1, 'tcp://*:2300', 100, False, -1)


        ## Throttle blocks ===============================================
        # uplink throttle
        self.blocks_throttle_UL_0 = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate,True)
        # downlink throttle
        self.blocks_throttle_DL_0 = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate,True)

        ## multiplier blocks one for each UE per uplink stream and downlink stream separately
        self.blocks_multiply_const_ue1_tx0 = blocks.multiply_const_cc(gain0) # UE1 TX0
        self.blocks_multiply_const_ue1_rx0 = blocks.multiply_const_cc(gain0) #  UE1 Rx0

        self.blocks_multiply_const_ue2_tx0 = blocks.multiply_const_cc(gain1) # UE2 TX0
        self.blocks_multiply_const_ue2_rx0 = blocks.multiply_const_cc(gain1) #  UE2 Rx0

        self.blocks_multiply_const_ue3_tx0 = blocks.multiply_const_cc(gain2) # UE3 TX0
        self.blocks_multiply_const_ue3_rx0 = blocks.multiply_const_cc(gain2) #  UE3 Rx0

        ## Adders for uplink per stream
        self.blocks_add_ul_rx0 = blocks.add_vcc(1)


        ##################################################
        # Connections
        ##################################################

        # =================== UPLINK ==================================

        # UE1 TX0
        self.connect((self.zmq_req_ue1_tx0, 0), (self.blocks_multiply_const_ue1_tx0, 0))
        # UE2 TX0
        self.connect((self.zmq_req_ue2_tx0, 0), (self.blocks_multiply_const_ue2_tx0, 0))
        # UE3 Tx0
        self.connect((self.zmq_req_ue3_tx0, 0), (self.blocks_multiply_const_ue3_tx0, 0))


        # Adding 3 UL streams together - stream 0
        self.connect((self.blocks_multiply_const_ue1_tx0, 0), (self.blocks_add_ul_rx0, 0))
        self.connect((self.blocks_multiply_const_ue2_tx0, 0), (self.blocks_add_ul_rx0, 1))
        self.connect((self.blocks_multiply_const_ue3_tx0, 0), (self.blocks_add_ul_rx0, 2))

        # throttle for UL stream 0
        self.connect((self.blocks_add_ul_rx0, 0), (self.blocks_throttle_UL_0, 0))

        # throttle -> gnB Rx0
        self.connect((self.blocks_throttle_UL_0, 0), (self.zmq_rep_gnb_rx0, 0))


        # =================== DOWNLINK ==================================
        # gNB Tx0 -> throttle
        self.connect((self.zmq_req_gnB_tx0, 0), (self.blocks_throttle_DL_0, 0))

            # throttle -> UE1 Rx0
        self.connect((self.blocks_throttle_DL_0, 0), (self.blocks_multiply_const_ue1_rx0, 0))
        self.connect((self.blocks_multiply_const_ue1_rx0, 0), (self.zmq_rep_ue1_rx0, 0))

            # throttle -> UE2 Rx0
        self.connect((self.blocks_throttle_DL_0, 0), (self.blocks_multiply_const_ue2_rx0, 0))
        self.connect((self.blocks_multiply_const_ue2_rx0, 0), (self.zmq_rep_ue2_rx0, 0))

            # throttle -> UE3 Rx0
        self.connect((self.blocks_throttle_DL_0, 0), (self.blocks_multiply_const_ue3_rx0, 0))
        self.connect((self.blocks_multiply_const_ue3_rx0, 0), (self.zmq_rep_ue3_rx0, 0))



    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "top_block")
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    # getters and setters
    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle_UL_0.set_sample_rate(self.samp_rate)
        self.blocks_throttle_DL_0.set_sample_rate(self.samp_rate)


    def get_gain0(self):
        return self.gain0
    
    def get_gain1(self):
        return self.gain1

    def get_gain2(self):
        return self.gain2

    def set_gain0(self, gain0):
        self.gain0 = gain0
        self.blocks_multiply_const_ue1_tx0.set_k(self.gain0)
        self.blocks_multiply_const_ue1_rx0.set_k(self.gain0)

    def set_gain1(self, gain1):
        self.gain1 = gain1
        self.blocks_multiply_const_ue2_tx0.set_k(self.gain1)
        self.blocks_multiply_const_ue2_rx0.set_k(self.gain1)

    def set_gain2(self, gain2):
        self.gain2 = gain2
        self.blocks_multiply_const_ue3_tx0.set_k(self.gain2)
        self.blocks_multiply_const_ue3_rx0.set_k(self.gain2)


def main(top_block_cls=top_block, options=None):

    if StrictVersion("4.5.0") <= StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()
    tb.start()
    tb.show()

    def sig_handler(sig=None, frame=None):
        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    def quitting():
        tb.stop()
        tb.wait()
    qapp.aboutToQuit.connect(quitting)
    qapp.exec_()


if __name__ == '__main__':
    main()