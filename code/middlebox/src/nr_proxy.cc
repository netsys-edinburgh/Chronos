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

#include <sys/stat.h>
#include <sstream>
#include <cstring>
#include <string>
#include "nr_proxy.h"
#include "nfapi_pnf.h"
#include "sc_receiver.h"

#define DISCOVERY_MSG_LEN 128
namespace
{
    Multi_UE_NR_Proxy *instance;
}
extern int g_all_acks_received;
extern uint8_t ue_finished[MAX_UES] ;
extern uint8_t gnb_finished[MAX_ENB];
extern uint8_t connected_ue_array[MAX_UES];
extern uint8_t connected_gnb_array[MAX_ENB];
extern uint8_t gnb_ue_count[MAX_ENB+MAX_UES];
extern uint16_t connected_gnb_count;
extern uint16_t connected_ue_count;

Multi_NR_UE_PNF::Multi_NR_UE_PNF(int pnf_id, int num_of_ues, int num_of_enbs, std::string enb_ip, std::string proxy_ip)
{
    num_ues = num_of_ues;
    num_enbs = num_of_enbs;

    id = pnf_id;
    
    configure_pnf_vnf(enb_ip, proxy_ip);
    oai_slot_init();
}

int Multi_NR_UE_PNF::get_id() {
    return id;
}

void Multi_NR_UE_PNF::configure_pnf_vnf(std::string enb_ip, std::string proxy_ip)
{
    vnf_ipaddr = enb_ip;
    pnf_ipaddr = proxy_ip;
    std::cout<<"VNF is on IP Address "<<vnf_ipaddr<<std::endl;
    std::cout<<"PNF is on IP Address "<<pnf_ipaddr<<std::endl;
}

void Multi_NR_UE_PNF::start_nf(softmodem_mode_t softmodem_mode)
{
    pthread_t thread;
    vnf_p5port = 50601 + id * ENB_PORT_DELTA;
    vnf_p7port = 50611 + id * ENB_PORT_DELTA;
    pnf_p7port = 50610 + id * ENB_PORT_DELTA; // This is the RX port from the eNB
    std::cout<<"VNF P5 Port "<<vnf_p5port<<std::endl;
    std::cout<<"VNF P7 Port "<<vnf_p7port<<std::endl;
    std::cout<<"PNF P7 Port "<<pnf_p7port<<std::endl;
    struct oai_task_args* args = (struct oai_task_args*)malloc(sizeof(struct oai_task_args));
    args->softmodem_mode = softmodem_mode;
    args->node_id = id;
    args->num_enbs = num_enbs;

    configure_nr_nfapi_pnf(id, vnf_ipaddr.c_str(), vnf_p5port, pnf_ipaddr.c_str(), pnf_p7port, vnf_p7port);

        if (pthread_create(&thread, NULL, &oai_slot_task, (void *)args) != 0)
        {
            NFAPI_TRACE(NFAPI_TRACE_ERROR, "pthread_create failed for calling oai_subframe_task");
        }
    
}

Multi_UE_NR_Proxy::Multi_UE_NR_Proxy(int num_of_ues, std::vector<std::string> gnb_ips, std::vector<int> gnb_ids, std::string proxy_ip, int proxy_id, std::string global_slotchecker_ip, std::string ue_ip)
{
    assert(instance == NULL);
    instance = this;
    for (int ue_idx = 0; ue_idx < num_of_ues; ue_idx++)
    {
        gNB_id[ue_idx] = 0;
    }

    pnf_ipaddr = proxy_ip;
    num_ues = num_of_ues;
	int num_of_gnbs = gnb_ips.size();
    num_gnb = num_of_gnbs;
    id = proxy_id;

    create_slot_checker_thread(proxy_id, proxy_ip.c_str(), global_slotchecker_ip.c_str());


    for (int i = 0; i < num_of_gnbs; i++)
    {
        nr_pnfs.push_back(Multi_NR_UE_PNF(gnb_ids[i], num_of_ues, num_of_gnbs, gnb_ips[i], proxy_ip));
    }
    for (int i = 0; i < num_of_gnbs; i++) {
        std::cout << "[NR Proxy] Configuring gNB #" << i << " at IP: " << gnb_ips[i] << std::endl;
        
        
    }
    for(int i = 0; i<1024; i++)
    {
        for(int j = 0; j<20; j++)
        {
            tx_data_dl_tti_checker[i][j] = 0;
        }
    }
    configure(ue_ip);
    configure_mobility_tables();
}

Multi_UE_NR_Proxy::Multi_UE_NR_Proxy(int num_of_ues, std::vector<std::string> gnb_ips,std::string proxy_ip, std::string ue_ip)
{
    assert(instance == NULL);
    instance = this;
    for (int ue_idx = 0; ue_idx < num_of_ues; ue_idx++)
    {
        gNB_id[ue_idx] = 0;
    }

    
    num_ues = num_of_ues;
	int num_of_gnbs = gnb_ips.size();

    for (int i = 0; i < num_of_gnbs; i++)
    {
        nr_pnfs.push_back(Multi_NR_UE_PNF(i, num_of_ues, num_of_gnbs, gnb_ips[i], proxy_ip));
    }
    for (int i = 0; i < num_of_gnbs; i++) {
        std::cout << "[NR Proxy] Configuring gNB #" << i << " at IP: " << gnb_ips[i] << std::endl;
        
    }
    for(int i = 0; i<1024; i++)
    {
        for(int j = 0; j<20; j++)
        {
            tx_data_dl_tti_checker[i][j] = 0;
        }
    }
    configure(ue_ip);
    configure_mobility_tables();
}

//todo modify start()
void Multi_UE_NR_Proxy::start(softmodem_mode_t softmodem_mode)
{


    int num_lte_pnfs = nr_pnfs.size();

    for (int i = 0; i < num_lte_pnfs; i++)
    {
        nr_pnfs[i].start_nf(softmodem_mode);
        usleep(100);
    }
    
    for (int i = 0; i < num_ues; i++)
    {
        threads.push_back(std::thread(&Multi_UE_NR_Proxy::receive_message_from_nr_ue, this, i));
    }
    for (auto &th : threads)
    {
        if(th.joinable())
        {
            th.join();
        }
    }
}

int Multi_UE_NR_Proxy::init_oai_socket(int rx_port, int ue_idx)
{
     {   //Setup Rx Socket
        printf("Setting up rx socket\n");
        std::cout<<"UE "<<ue_idx<<" is on port "<<rx_port<<std::endl;
        memset(&address_rx_, 0, sizeof(address_rx_));
        address_rx_.sin_family = AF_INET;
        address_rx_.sin_addr.s_addr = inet_addr(pnf_ipaddr.c_str());
        address_rx_.sin_port = htons(rx_port);
        ue_rx_socket_ = socket(address_rx_.sin_family, SOCK_DGRAM, 0);
        ue_rx_socket[ue_idx] = ue_rx_socket_;

        if (ue_rx_socket_ < 0)
        {
            NFAPI_TRACE(NFAPI_TRACE_ERROR, "socket: %s", ERR);
            return -1;
        }
        if (bind(ue_rx_socket_, (struct sockaddr *)&address_rx_, sizeof(address_rx_)) < 0)
        {
            NFAPI_TRACE(NFAPI_TRACE_ERROR, "bind failed in init_oai_socket: %s\n", strerror(errno));
            close(ue_rx_socket_);
            ue_rx_socket_ = -1;
            return -1;
        }
    }
    return 0;
}

void Multi_UE_NR_Proxy::configure_mobility_tables()
{

    // initialise the structure
    for(long unsigned int i = 0; i < nr_pnfs.size(); i++){
        int pnf_id = nr_pnfs[i].get_id();
        std::unordered_set<int> * mobility = new std::unordered_set<int>;
        mobility_info_map[pnf_id] = mobility_info_map[i] = std::shared_ptr<std::unordered_set<int>>(mobility);
    }
    std::cout<<nr_pnfs.size()<<std::endl;
    // fill the structure
   // std::cout<<"Opening file \n";
//    std::string scenario_file_name = "/local/repository/scripts/ran/start_param";
  //  std::ifstream scenario_file;
   // print_mobility_table();
    // scenario_file.open(scenario_file_name.c_str(),std::ios::in);
    // if(!scenario_file)
    //     std::cout<<"File didnt open correctly\n";
    // while (std::getline(scenario_file, UE_ID_str, ',')) {
    //     std::cout << "UE_ID: " << UE_ID_str << " " ; 
    //     std::getline(scenario_file, source_eNB, ',') ;
    //     std::cout << "source_eNB: " << source_eNB << " " ;
    //     std::getline(scenario_file, target_eNB) ;
    //     std::cout << "target_eNB: " << target_eNB << "\n"  ;
    //     std::cout << std::flush;
    //     uint16_t new_source_enb = atoi(source_eNB.c_str());
    //     uint16_t new_target_enb = atoi(target_eNB.c_str());
    //     int ue_id = atoi(UE_ID_str.c_str());

    //     std::cout << "Inserting UE ID " << ue_id << " (socket: " << ue_id << ") to new source eNB ID " << new_source_enb << "\n";
    //     mobility_info_map[new_source_enb]->insert(ue_id);

    //     std::cout << "Inserting UE ID " << ue_id << " (socket: " << ue_id << ") to new target eNB ID " << new_target_enb << "\n";
    //     mobility_info_map[new_target_enb]->insert(ue_id);
    // }
    // print_mobility_table();
    // std::cout<<"Closing file \n";
    // scenario_file.close();


}

void Multi_UE_NR_Proxy::print_mobility_table()
{
    std::cout << "====================================\n";
    std::cout << "Printing mobility table:\n";
    for(const auto& map_elm : mobility_info_map)
    {
        std::cout << map_elm.first << ": ";
        for(const auto& set_elm : *map_elm.second)
        {
            std::cout << set_elm << ", ";
        }
        std::cout << "\n";
    }
    std::cout << "====================================\n";
}



void Multi_UE_NR_Proxy::configure(std::string ue_ip)
{
    oai_ue_ipaddr = ue_ip;

    std::cout<<"OAI-UE is on IP Address "<<oai_ue_ipaddr<<std::endl;
    
    for (int ue_idx = 0; ue_idx < num_ues; ue_idx++)
    {
        int oai_rx_ue_port = BASE_RX_NR_UE_PORT + ue_idx * UE_PORT_DELTA;
        // int oai_tx_ue_port = 3612 + ue_idx * port_delta;
        init_oai_socket(oai_rx_ue_port, ue_idx);
    }
}

void Multi_UE_NR_Proxy::receive_message_from_nr_ue(int ue_idx)
{
      // Setup tx socket first
    
        int tmp_sock;
        int len;
        struct sockaddr_in ue_discovered_addr;
        struct sockaddr_in send_bind_addr;
        socklen_t addr_len = sizeof(ue_discovered_addr);
        uint8_t buffer[NFAPI_MAX_PACKED_MESSAGE_SIZE];

        printf("Setting up downlink socket for UE %d\n", ue_idx);
        usleep(20);
        /* Create tx socket */
        if ((tmp_sock = socket(AF_INET, SOCK_DGRAM, 0)) < 0)
        {
            printf("Error creating downlink socket for UE %d: %s", ue_idx, strerror(errno));
            return;
        }

        send_bind_addr.sin_family = AF_INET;
        printf("Opening UE discovery port on IP %s\n", pnf_ipaddr.c_str());
        send_bind_addr.sin_addr.s_addr = inet_addr(pnf_ipaddr.c_str());

        /* Tx port formula: 3212 + ue_idx * port_delta; */
        printf("Binding downlink socket for UE %d to port %d\n", ue_idx, BASE_TX_NR_UE_PORT + ue_idx * UE_PORT_DELTA);
        send_bind_addr.sin_port = htons(BASE_TX_NR_UE_PORT + ue_idx * UE_PORT_DELTA);
        
        /* Bind */
        if (bind(tmp_sock, (struct sockaddr *)&send_bind_addr, sizeof(struct sockaddr)) == -1)
        {
            printf("Error binding downlink socket for UE %d: %s", ue_idx, strerror(errno));
            return ;
        }

        /* Receive the discovery packet on the tx socket and store the UE address */
        printf("Waiting for discovery message %d\n", ue_idx);
        len = recvfrom(tmp_sock, buffer, sizeof(buffer), 0, (struct sockaddr *)&ue_discovered_addr, &addr_len);
        if (len == -1)
        {
            printf("Recv failure (%d): %s", errno, strerror(errno));
            return;
        }

        uint16_t new_source_gnb = (uint16_t) buffer[0];
        std::cout << "Inserting UE ID " << ue_idx << " (socket: " << ue_idx << " ) to new source gNB ID " << new_source_gnb << "\n";
        mobility_info_map[new_source_gnb]->insert(ue_idx);
        mobility_info_map[new_source_gnb]->insert(ue_idx); // Add the UE to the mobility table of the gNB
        print_mobility_table();
        printf("Got discovery message for UE %d, start at gNB %d\n", ue_idx,new_source_gnb);
        fflush(stdout);
        
        /* Connect socket to the UE address of the packet received (ue_discovered_addr). */
        if (connect(tmp_sock, (struct sockaddr *)&ue_discovered_addr, addr_len) < 0)
        {
            perror("connect");
            printf("Error connecting downlink socket for UE %d: %s", ue_idx, strerror(errno));
            return;
        }

        /* Save the tx socket for the ue in the proxy */
        ue_tx_socket[ue_idx] = tmp_sock;

        /* Print client network info */
        char *ip_client = inet_ntoa(ue_discovered_addr.sin_addr);
        uint16_t port_client = htons(ue_discovered_addr.sin_port);
        printf("UE %d downlink socket connected to %s:%d\n", ue_idx, ip_client, (int) port_client);
        fflush(stdout);
    
        // Receive messages from UE
    addr_len = sizeof(address_rx_);
    bool first_slot_ind = false;
    // === Wait for messages from UE ===
    while(true)
    {
        int buflen = recvfrom(ue_rx_socket[ue_idx], buffer, sizeof(buffer), 0, (sockaddr *)&address_rx_, &addr_len);
        if (buflen == -1)
        {
            NFAPI_TRACE(NFAPI_TRACE_ERROR, "Recvfrom failed %s", strerror(errno));
            return ;
        }
        if (buflen == 4)
        {
            //NFAPI_TRACE(NFAPI_TRACE_INFO , "Dummy frame");
            continue;

        }
        else
        {
            nfapi_p7_message_header_t header;
            if (nfapi_p7_message_header_unpack(buffer, buflen, &header, sizeof(header), NULL) < 0)
            {
                NFAPI_TRACE(NFAPI_TRACE_ERROR, "Header unpack failed for standalone pnf");
                return ;
            }
            uint16_t sfn_slot = nfapi_get_sfnslot(buffer, buflen);
            NFAPI_TRACE(NFAPI_TRACE_DEBUG , "(Proxy) Proxy has received %d uplink message from OAI UE at socket. Frame: %d, Slot: %d",
                    header.message_id, NFAPI_SFNSLOT2SFN(sfn_slot), NFAPI_SFNSLOT2SLOT(sfn_slot));
                    
             if(header.message_id == NFAPI_NR_PHY_MSG_TYPE_SLOT_INDICATION){
                     if(first_slot_ind == false){
                        first_slot_ind = true;
                        std::cout<<"First slot indication received from UE "<<ue_idx<<"\n";
                        connected_ue_count++;
                        connected_ue_array[ue_idx] = 1;
                        std::cout<<"Connected UE count : "<<connected_ue_count<<std::endl;
                    }
                    else{
                    // std::cout<<"Subframe indication received Form UE" <<ue_idx<<std::endl;
                    ue_finished[ue_idx]++;
                    }
                    continue;
             }
             
        }

        oai_slot_handle_msg_from_ue(new_source_gnb, buffer, buflen, ue_idx + 2);
    }
}


    void  Multi_UE_NR_Proxy::oai_gnb_downlink_nfapi_task(const std::shared_ptr<const std::unordered_set<int>>& ue_set, uint16_t id, void *msg_org)
    {
    static bool first_slot_ind[MAX_ENB];
    lock_guard_t lock(mutex);
    nfapi_p7_message_header_t *pHeader = (nfapi_p7_message_header_t *)msg_org;
    pHeader->phy_id = id;
    // printf("[Proxy] Received message from gNB %d with message ID %d\n", id, pHeader->message_id);
    char buffer[NFAPI_MAX_PACKED_MESSAGE_SIZE];
    int encoded_size = nfapi_nr_p7_message_pack(msg_org, buffer, sizeof(buffer), nullptr);
    if (encoded_size <= 0)
    {
        NFAPI_TRACE(NFAPI_TRACE_ERROR, "nfapi_nr_p7_message_pack failed");
        return;
    }

    union
    {
        nfapi_p7_message_header_t header;
        nfapi_nr_dl_tti_request_t dl_tti_request;
        nfapi_nr_tx_data_request_t tx_data_req;
        nfapi_nr_ul_dci_request_t ul_dci_req;
        nfapi_nr_ul_tti_request_t ul_tti_request;
        nfapi_nr_slot_indication_scf_t slot_ind;
    } msg;

    if (nfapi_nr_p7_message_unpack((void *)buffer, encoded_size, &msg, sizeof(msg), NULL) != 0)
    {
        NFAPI_TRACE(NFAPI_TRACE_ERROR, "nfapi_nr_p7_message_unpack failed NEM ID: %d", 1);
        return;
    }
    static int print_limit = 0;
    for(int ue_idx : *ue_set)
    {   
            if (ue_tx_socket[ue_idx] < 2)
            {
                if(print_limit == 1000){
                    printf("[proxy] (print limited )UE %d not connected, skipping message forwarding\n", ue_idx);
                    print_limit = 0;
                }
                else{
                    print_limit++;
                }

                //NFAPI_TRACE(NFAPI_TRACE_ERROR, "UE %d not connected, skipping message forwarding", ue_idx);
                continue;
            }
            address_tx_.sin_port = htons(3612 + ue_idx * port_delta);
            switch (msg.header.message_id)
            {

            case NFAPI_NR_PHY_MSG_TYPE_DL_TTI_REQUEST:
            {
                
                int dl_sfn = msg.dl_tti_request.SFN;
                int dl_slot = msg.dl_tti_request.Slot;
                
                if(tx_data_dl_tti_checker[dl_sfn][dl_slot] == 0)
                {
                    // printf("[%d.%d] First received dl tti request size: %d checker %d \n", dl_sfn, dl_slot, encoded_size, tx_data_dl_tti_checker[dl_sfn][dl_slot]);

                    tx_data_dl_tti_checker[dl_sfn][dl_slot]= 1;

                }
                else if(tx_data_dl_tti_checker[dl_sfn][dl_slot] == 1)
                {
                //    printf("[%d.%d] Second received dl tti request size: %d checker %d \n", dl_sfn, dl_slot, encoded_size, tx_data_dl_tti_checker[dl_sfn][dl_slot]);

                   tx_data_dl_tti_checker[dl_sfn][dl_slot]= 0;
                    
                }
                else if(tx_data_dl_tti_checker[dl_sfn][dl_slot] == 2)
                {
                    // printf("[%d.%d] We shouldn't be here \n", dl_sfn, dl_slot);
                    // exit(0);
                    return;
                }
                uint16_t dl_numPDU = msg.dl_tti_request.dl_tti_request_body.nPDUs;
                NFAPI_TRACE(NFAPI_TRACE_INFO , "(Proxy UE) Prior to sending dl_tti_req to OAI UE. Frame: %d,"
                        " Slot: %d, Number of PDUs: %u",
                        dl_sfn, dl_slot, dl_numPDU);
                assert(ue_tx_socket[ue_idx] > 2);
                if (send(ue_tx_socket[ue_idx], buffer, encoded_size, 0) < 0)
                {
                    NFAPI_TRACE(NFAPI_TRACE_ERROR, "Send NFAPI_NR_PHY_MSG_TYPE_DL_TTI_REQUEST to OAI UE failed");
                }
                else
                {
                    NFAPI_TRACE(NFAPI_TRACE_INFO , "NFAPI_NR_PHY_MSG_TYPE_DL_TTI_REQUEST forwarded from Proxy to UE");
                }
                break;
            }

            case NFAPI_NR_PHY_MSG_TYPE_TX_DATA_REQUEST:{
                int dl_sfn = msg.tx_data_req.SFN;
                int dl_slot = msg.tx_data_req.Slot;
                if(tx_data_dl_tti_checker[dl_sfn][dl_slot] == 0)
                   {
                   // printf("[%d.%d] First received tx data request size: %d checker %d \n", dl_sfn, dl_slot, encoded_size, tx_data_dl_tti_checker[dl_sfn][dl_slot]);

                    tx_data_dl_tti_checker[dl_sfn][dl_slot]= 1;
                }
                else if(tx_data_dl_tti_checker[dl_sfn][dl_slot] == 1)
                {
                    // printf("[%d.%d] Second received tx data request size :%d checker %d \n", dl_sfn, dl_slot, encoded_size, tx_data_dl_tti_checker[dl_sfn][dl_slot]);
                  
                   tx_data_dl_tti_checker[dl_sfn][dl_slot]= 0;
                }
                else if(tx_data_dl_tti_checker[dl_sfn][dl_slot] == 2)
                {
                    // printf("[%d.%d] We shouldn't be here  \n", dl_sfn, dl_slot);
                    // exit(0);
                    // return;
                }
                assert(ue_tx_socket[ue_idx] > 2);
                if (send(ue_tx_socket[ue_idx], buffer, encoded_size, 0) < 0)
                {
                    NFAPI_TRACE(NFAPI_TRACE_ERROR, "Send NFAPI_NR_PHY_MSG_TYPE_TX_DATA_REQUEST to OAI UE failed");
                }
                else
                {
                    NFAPI_TRACE(NFAPI_TRACE_INFO , "NFAPI_NR_PHY_MSG_TYPE_TX_DATA_REQUEST forwarded from Proxy to UE");
                }
                break;
            }
            case NFAPI_NR_PHY_MSG_TYPE_UL_TTI_REQUEST:{
                assert(ue_tx_socket[ue_idx] > 2);
                if (send(ue_tx_socket[ue_idx], buffer, encoded_size, 0) < 0)
                {
                    NFAPI_TRACE(NFAPI_TRACE_ERROR, "Send NFAPI_NR_PHY_MSG_TYPE_UL_TTI_REQUEST to OAI UE failed");
                }
                else
                {
                    NFAPI_TRACE(NFAPI_TRACE_INFO , "NFAPI_NR_PHY_MSG_TYPE_UL_TTI_REQUEST forwarded from Proxy to UE");
                }
                break;
            }
            case NFAPI_NR_PHY_MSG_TYPE_UL_DCI_REQUEST:{
                assert(ue_tx_socket[ue_idx] > 2);
                if (send(ue_tx_socket[ue_idx], buffer, encoded_size, 0) < 0)
                {
                    NFAPI_TRACE(NFAPI_TRACE_ERROR, "Send NFAPI_NR_PHY_MSG_TYPE_UL_DCI_REQUEST to OAI UE failed");
                }
                else
                {
                    NFAPI_TRACE(NFAPI_TRACE_INFO , "NFAPI_NR_PHY_MSG_TYPE_UL_DCI_REQUEST forwarded from Proxy to UE");
                }
                break;
            }
            case NFAPI_NR_PHY_MSG_TYPE_SLOT_INDICATION:{
                if(first_slot_ind[id] == false){
                        first_slot_ind[id] = true;
                        std::cout<<"First slot indication received\n";
                        connected_gnb_count++;  
                        connected_gnb_array[id] = 1;
                        std::cout<<"Connected gNB count : "<<connected_gnb_count<<std::endl;
                        }
                        gnb_finished[id]++;
                break;
                assert(ue_tx_socket[ue_idx] > 2);
                if (send(ue_tx_socket[ue_idx], buffer, encoded_size, 0) < 0)
                {
                    NFAPI_TRACE(NFAPI_TRACE_ERROR, "Send NFAPI_NR_PHY_MSG_TYPE_SLOT_INDICATION to OAI UE failed");
                }
                else
                {
                    NFAPI_TRACE(NFAPI_TRACE_INFO , "NFAPI_NR_PHY_MSG_TYPE_SLOT_INDICATION forwarded from Proxy to UE");
                }
                break;
            }
            default:
                NFAPI_TRACE(NFAPI_TRACE_INFO , "Unhandled message at Proxy message_id: %u", msg.header.message_id);
                
                break;
            }
    }
}

void  Multi_UE_NR_Proxy::pack_and_send_downlink_sfn_slot_msg(const std::shared_ptr<const std::unordered_set<int>>& ue_set, uint16_t id, uint16_t sfn_slot)
{
    lock_guard_t lock(mutex);
    sfn_slot_info_t sfn_sf_info;
    sfn_sf_info.phy_id = id;
    sfn_sf_info.sfn_slot = sfn_slot;
    
    /* Each eNB send sfn_sf to ALL UEs (even those not connected to it) */
    static int limit_print = 0;
    for( auto ue_idx : *ue_set)
    { 
            if (ue_tx_socket[ue_idx] < 2)
            {
                return;
            }
            
            if (send(ue_tx_socket[ue_idx], &sfn_sf_info, sizeof(sfn_slot_info_t), 0) < 0)
            {
                if(limit_print == 1000){
                    printf("(Proxy) (Printing every 1000 slots)Send sfn_sf_tx to OAI UE FAIL Frame: %d,Subframe: %d, ENB: %d\n", NFAPI_SFNSLOT2SFN(sfn_slot), NFAPI_SFNSLOT2SLOT(sfn_slot), id);
                    limit_print  = 0;
                }
                else{
                    limit_print++;
                }

            }
    }
    
}
void transfer_downstream_nfapi_msg_to_nr_proxy(uint16_t phy_id, void *msg)
{   
    /* Grab the UE set that belongs to this eNB. */
    auto it = instance->mobility_info_map.find(phy_id);
    if (it == instance->mobility_info_map.end() || !it->second)
        return;                     // nothing to do 
    instance->oai_gnb_downlink_nfapi_task(it->second, phy_id, msg);
}

bool check_tx_data_dl_tti_checker(uint16_t sfn, uint16_t slot)
{
    if(instance == NULL)
    {
        return false;
    }

    if(instance->tx_data_dl_tti_checker[sfn][slot] == 0)
    {
        return true;
    }
    else if(instance->tx_data_dl_tti_checker[sfn][slot] == 1)
    {
        return false;
    }
    else if(instance->tx_data_dl_tti_checker[sfn][slot] == 2)
    {

        return true;
    }
    else
    {
        printf("We shouldn't be here in check_tx_data_dl_tti_checker\n");
        exit(0);
        return false;
    }
}
void transfer_downstream_sfn_slot_to_proxy( uint16_t phy_id,  uint16_t sfn_slot)
{

   /* Grab the UE set that belongs to this eNB. */
    auto it = instance->mobility_info_map.find(phy_id);
    if (it == instance->mobility_info_map.end() || !it->second)
        return;                     // nothing to do
    instance->pack_and_send_downlink_sfn_slot_msg(it->second , phy_id, sfn_slot);
}
