#/*
# * Licensed to the EPYSYS SCIENCE (EpiSci) under one or more
# * contributor license agreements.
# * The EPYSYS SCIENCE (EpiSci) licenses this file to You under
# * the Episys Science (EpiSci) Public License (Version 1.1) (the "License"); you may not use this file
# * except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      https://github.com/EpiSci/oai-lte-5g-multi-ue-proxy/blob/master/LICENSE
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# *-------------------------------------------------------------------------------
# * For more information about EPYSYS SCIENCE (EpiSci):
# *      bo.ryu@episci.com
# */

#pragma once

#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <sys/time.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <netinet/sctp.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <errno.h>
#include <stdarg.h>
#include <string>
#include <cstring>
#include <mutex>
#include <assert.h>
#include <iostream>
#include <memory>
#include <vector>
#include <thread>
#include "proxy.h"
#include <unordered_map>
#include <unordered_set>
#define UE_PORT_DELTA 2
#define ENB_PORT_DELTA 8
#define BASE_RX_NR_UE_PORT 3611
#define BASE_TX_NR_UE_PORT 3612
#define MAX_ENB 950
#define MAX_UES 2000
#define MAX_ENBS 950

class Multi_NR_UE_PNF
{
public:
    Multi_NR_UE_PNF(int id, int num_of_ues, int num_of_enbs, std::string enb_ip, std::string proxy_ip);
    ~Multi_NR_UE_PNF() = default;
    void configure_pnf_vnf(std::string enb_ip, std::string proxy_ip);
    void start_nf(softmodem_mode_t softmodem_mode);
    int get_id();
private:
    std::string oai_ue_ipaddr;
    std::string vnf_ipaddr;
    std::string pnf_ipaddr;
    int vnf_p5port = -1;
    int vnf_p7port = -1;
    int pnf_p7port = -1;
    int id;
    int num_enbs;
};

class Multi_UE_NR_Proxy
{
public:
 Multi_UE_NR_Proxy(int num_of_ues,
                    const std::vector<std::string> gnb_ips,
                    const std::vector<int> gnb_ids, // NEW
					const std::string proxy_ip,
                    int proxy_id,
                    const std::string global_slotchecker_ip, // NEW
                   const std::string ue_ip);
     Multi_UE_NR_Proxy(int num_of_ues,
                    const std::vector<std::string> gnb_ips,
					const std::string proxy_ip,
                   const std::string ue_ip);
    Multi_UE_NR_Proxy() = default;
    void configure(std::string ue_ip);
    int init_oai_socket(int rx_port, int ue_idx);
    void oai_gnb_downlink_nfapi_task(const std::shared_ptr<const std::unordered_set<int>>& ue_set, uint16_t id, void *msg);
    void testcode_tx_packet_to_UE( int ue_tx_socket_);
    void pack_and_send_downlink_sfn_slot_msg(const std::shared_ptr<const std::unordered_set<int>>& ue_set,uint16_t id, uint16_t sfn_slot);
    int discover_and_connect_ue(int ue_idx);  //TODO new
    void receive_message_from_nr_ue(int ue_id);
    void send_nr_ue_to_gnb_msg(void *buffer, size_t buflen);
    void send_received_msg_to_proxy_queue(void *buffer, size_t buflen);
    void send_uplink_oai_msg_to_proxy_queue(void *buffer, size_t buflen);
    void start(softmodem_mode_t softmodem_mode);
    void configure_mobility_tables();
    void print_mobility_table();
    uint8_t tx_data_dl_tti_checker[1024][20];
    std::vector<Multi_NR_UE_PNF> nr_pnfs;
    std::unordered_map<uint16_t, std::shared_ptr<std::unordered_set<int>>> mobility_info_map;
private:
    std::string oai_ue_ipaddr;
    std::string vnf_ipaddr;
    std::string pnf_ipaddr;
    int vnf_p5port = -1;
    int vnf_p7port = -1;
    int pnf_p7port = -1;
    uint16_t gNB_id[MAX_ENB]; // To identify the destination in uplink
    std::uint16_t u16SequenceNumber_ = 0;
    struct sockaddr_in address_tx_;
    struct sockaddr_in address_rx_;
    int ue_tx_socket_ = -1;
    int ue_rx_socket_ = -1;
    int ue_rx_socket[MAX_UES];
    int ue_tx_socket[MAX_UES];

    uint16_t id;
    typedef struct sfn_slot_info_s
    {
        uint16_t phy_id;
        uint16_t sfn_slot;
    } sfn_slot_info_t;
    std::recursive_mutex mutex;
    using lock_guard_t = std::lock_guard<std::recursive_mutex>;
    std::vector<std::thread> threads;
    bool stop_thread = false;
    int port_delta = 2;


    int connected_ue_count   = 0;          // TODO ★ NEW
    uint8_t connected_ue[MAX_UES]{};           //TODO  ★ NEW; 1 = connected
};
