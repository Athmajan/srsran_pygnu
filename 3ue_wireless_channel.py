from gnuradio import channels
from gnuradio import blocks
from gnuradio import gr
from gnuradio import zeromq
import sys
import signal
import threading
import argparse

BETA_FIFO = '/tmp/beta_fifo'
gain_levels = [
1.0,  .8,  .6, .5,   .4, .35,  .3, .25, .22, .20, 
.18, .16, .14, .12, .10, .08, .06]
gain_level_duration = 30

total_loops = 1

class athena_wireless_channel(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "3UE_Athena")

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 23.04e6
        self.gain2 = gain2 = 0.06
        self.gain1 = gain1 = 0.04   
        self.gain0 = gain0 = 0.05


        self.noise_level_ue1 = noise_level_ue1 = 0.01
        self.noise_level_ue2 = noise_level_ue2 = 0.01
        self.noise_level_ue3 = noise_level_ue3 = 0.01

        self.ul_gain_ue1 = self.dl_gain_ue1 = 1 
        self.ul_gain_ue2 = self.dl_gain_ue2 = 1 
        self.ul_gain_ue3 = self.dl_gain_ue3 = 1 

        ##################################################
        # Blocks
        ##################################################

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

        # UL channel of UE1
        self.uplink_ue1 = channels.channel_model(
            noise_voltage=noise_level_ue1,
            noise_seed=0)
        self.uplink_ue1.set_block_alias("UE1 UPLINK")

        # UL channel of UE2
        self.uplink_ue2 = channels.channel_model(
            noise_voltage=noise_level_ue2,
            noise_seed=0)
        self.uplink_ue2.set_block_alias("UE2 UPLINK")

        # UL channel of UE3
        self.uplink_ue3 = channels.channel_model(
            noise_voltage=noise_level_ue3,
            noise_seed=0)
        self.uplink_ue3.set_block_alias("UE3 UPLINK")

        # DL channel of UE1
        self.downlink_ue1 = channels.channel_model(
            noise_voltage=noise_level_ue1,
            noise_seed=0)
        self.downlink_ue1.set_block_alias("UE1 DOWNLINK")

        # DL channel of UE2
        self.downlink_ue2 = channels.channel_model(
            noise_voltage=noise_level_ue2,
            noise_seed=0)
        self.downlink_ue2.set_block_alias("UE2 DOWNLINK")

        # DL channel of UE3
        self.downlink_ue3 = channels.channel_model(
            noise_voltage=noise_level_ue3,
            noise_seed=0)
        self.downlink_ue3.set_block_alias("UE3 DOWNLINK")


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

    def get_noise_level_ue1(self):
        return self.noise_level_ue1

    def get_noise_level_ue2(self):
        return self.noise_level_ue2

    def get_noise_level_ue3(self):
        return self.noise_level_ue3


    def set_multiply_level_ue1(self, multiply_level_ue1):
        self.ul_gain_ue1 = multiply_level_ue1
        self.dl_gain_ue1 = multiply_level_ue1
        self.blocks_multiply_const_ue1_tx0.set_k(self.ul_gain_ue1)
        self.blocks_multiply_const_ue1_rx0.set_k(self.dl_gain_ue1)

    def set_multiply_level_ue2(self, multiply_level_ue2):
        self.ul_gain_ue2 = multiply_level_ue2
        self.dl_gain_ue2 = multiply_level_ue2
        self.blocks_multiply_const_ue2_tx0.set_k(self.ul_gain_ue2)
        self.blocks_multiply_const_ue2_rx0.set_k(self.dl_gain_ue2)

    def set_multiply_level_ue3(self, multiply_level_ue3):
        self.ul_gain_ue3 = multiply_level_ue3
        self.dl_gain_ue3 = multiply_level_ue3
        self.blocks_multiply_const_ue3_tx0.set_k(self.ul_gain_ue3)
        self.blocks_multiply_const_ue3_rx0.set_k(self.dl_gain_ue3)

    def set_noise_level_ue1(self, noise):
        self.noise_level_ue1 = noise
        self.uplink_ue1.set_noise_voltage(noise)
        self.downlink_ue1.set_noise_voltage(noise)

    def set_noise_level_ue2(self, noise):
        self.noise_level_ue2 = noise
        self.uplink_ue2.set_noise_voltage(noise)
        self.downlink_ue2.set_noise_voltage(noise)

    def set_noise_level_ue3(self, noise):
        self.noise_level_ue3 = noise
        self.uplink_ue3.set_noise_voltage(noise)
        self.downlink_ue3.set_noise_voltage(noise)


import time
def automated_monitoring_thread(tb):    
    is_file_open = False
    while (not is_file_open):
        try:
            with open(BETA_FIFO, mode = 'wb') as file_write:
                is_file_open = True
                print('Opening beta fifo socket successful. Going to sleep')                
                time.sleep(10) # this sleep is necessary as the echo_to_cpuset and the iperf startup scripts are initiated    
                loops = 0
                while (True):
                    current_gain_level_idx = 0
                    direction = 1
                    hit_low_snr_first_time = True
                    while (1):
                        tb.set_multiply_level_ue1(gain_levels[current_gain_level_idx])
                        current_gain_level_bytes = (int(gain_levels[current_gain_level_idx]* 1000)).to_bytes(2, byteorder='little')
                        file_write.write(current_gain_level_bytes)
                        file_write.flush()
                        print('Setting UE Gain level {}'.format(gain_levels[current_gain_level_idx]))
                        time.sleep(gain_level_duration)
                        if (current_gain_level_idx + direction == len(gain_levels) or
                            current_gain_level_idx + direction == -1):
                            if (current_gain_level_idx == len(gain_levels) - 1 and hit_low_snr_first_time):
                                hit_low_snr_first_time = False
                                continue
                            elif (current_gain_level_idx == 0):
                                break
                            direction = -direction
                        
                        current_gain_level_idx += direction
        except FileNotFoundError as e:
            print('error')
        finally:
            print('Gracefully exiting...')


def main(top_block_cls=athena_wireless_channel, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    t2 = threading.Thread(target=automated_monitoring_thread, args=(tb, ))
    
    t2.start()
    t2.join()
    tb.wait()


if __name__ == '__main__':
    main()