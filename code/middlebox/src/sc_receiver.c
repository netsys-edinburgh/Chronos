#include "sc_receiver.h"

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <pthread.h>
#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
int g_all_acks_received;
int fd[10];
uint8_t ue_finished[MAX_UES]; 
uint8_t gnb_finished[MAX_ENB]; 
uint8_t connected_ue_array[MAX_UES];
uint8_t connected_gnb_array[MAX_ENB];
uint16_t connected_ue_count = 0 ;
uint16_t connected_gnb_count = 0;
int num_component;
struct sockaddr_in componentaddr[10];
int main_done = 0;
uint8_t gslot = 2;
 

int received_all_acks(uint8_t * acks, uint16_t num_ues_enbs) {
    for (int i = 0; i < num_ues_enbs; i++) {
        // printf("Ack %d: %d\n", i, acks[i]);
        if (acks[i] == 0) {
            return 0;
        }
    }
    return 1;
}

int connect_to_component_udp(){
    int sockfd;
    // Creating socket file descriptor
    if ( (sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0 ) {
        printf("Failed to create socket");
        return 1;
    }
    return sockfd;
}

int send_slot_start(uint8_t num_to_send){
    // printf("Sending slot start\n");
    for(int i=0;i<num_component;i++){
        //  printf("Sending to component %d\n", i);
      sendto(fd[i], (uint8_t *) &num_to_send, sizeof(num_to_send), MSG_CONFIRM, (const struct sockaddr *) &componentaddr[i], sizeof(componentaddr[i]));
    }
    return 0;
}

int send_exit(uint8_t num_to_send){
    printf("Sending exit\n");
    for(int i=0;i<num_component;i++){
         printf("Sending %d to component %d\n ", num_to_send, i);
     sendto(fd[i], (uint8_t *) &num_to_send, sizeof(num_to_send), MSG_CONFIRM, (const struct sockaddr *) &componentaddr[i], sizeof(componentaddr[i]));
}
     return 0;
}

int send_start(uint8_t num_to_send){
    printf("Sending start\n");
    for(int i=0;i<num_component;i++){
         printf("Sending %d to component %d\n ", num_to_send, i);
     sendto(fd[i], (uint8_t *) &num_to_send, sizeof(num_to_send), MSG_CONFIRM, (const struct sockaddr *) &componentaddr[i], sizeof(componentaddr[i]));
}
     return 0;
}

int get_all_acks(int sock, uint16_t num_ues_enbs) {
    uint8_t acks[num_ues_enbs];
    bzero(&acks, sizeof(uint8_t) * num_ues_enbs);
    
    while (1) {
        // check to see if we have received all the acks
        if (received_all_acks(acks, num_ues_enbs)) {
            break;
        }

        // if we reach here then we are still waiting for at least one ack
        uint8_t buffer[100];
        int n = recvfrom(sock, buffer, sizeof(buffer), MSG_WAITALL, NULL, NULL);

        // check ack length is correct
        if (n != sizeof(uint8_t)*2) {
            printf("Error, received message of size %d\n", n);
             printf("%s \n", buffer);
	    continue;           return 1;
        }

        // extract the ack from the message
        // uint16_t received_ack;
        // memcpy(&received_ack, buffer, n);
        uint8_t id = buffer[0];

//        uint8_t slot = buffer[1];
        // check this ack is within range
        if (id >= num_ues_enbs) {
            printf("Error, ack %d outside of range (0-%d)\n", id, num_ues_enbs);
            return 1;
        }
        // printf("[%d]Received ack %d\n", gslot, id);
        // check we haven't received this ack before
        if (acks[id] != 0) {
            printf("Error, duplicate ack received for %d\n", id);
            return 1;
        }

        // store the ack
        acks[id] = 1;

        // log
        //printf("Acknowledgement from %d\n", received_ack);
    }

    return 0;
}


int udp_socket_open(struct sockaddr_in addr) {;

    int sock_udp = socket(AF_INET, SOCK_DGRAM, 0);
    assert(sock_udp >= 0); // Failed to setup UDP socket

    int bind_outcome = bind(sock_udp,(struct sockaddr *) &addr, sizeof(addr));
    assert(bind_outcome >= 0); // Failed to bind socket

    return sock_udp;
}


void udp_socket_connect(int sock, struct sockaddr_in addr) {
    int connect_outcome = connect(sock, (struct sockaddr *) &addr, sizeof(addr));
    assert(connect_outcome >= 0); // Failed to connect socket
}


struct sockaddr_in create_address(char * ip_address, uint16_t port) {
    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_addr.s_addr = inet_addr(ip_address);
    address.sin_family = AF_INET;
    address.sin_port = htons(port);
    return address;
}


void * main_loop(void * raw_args) {

    struct sched_param schedParam;
    schedParam.__sched_priority = 99;

    assert(sched_setscheduler(0, SCHED_RR, &schedParam) == 0);

    main_loop_args_t * args = (main_loop_args_t *) raw_args;

    struct sockaddr_in global_sc_addr = create_address(args->global_sc_ip, 6000);

    int sock = udp_socket_open(create_address(args->proxy_ip, 4322));

    int really_finished_gnb;
    int really_finished_ue;

    while (1) {
        int check_times = 2500;
        int current_round_ue[MAX_UES];
        int current_round_enb[MAX_ENB];
        for(int i=0;i<MAX_UES;i++){
            current_round_ue[i] = 0;
        }
        for(int i=0;i<MAX_ENB;i++){
            current_round_enb[i] = 0;
        }

        really_finished_gnb = 0;
        really_finished_ue = 0;
        check_times = 1000;
        //current_round[100];
        while (check_times--) {
            int all_finished = 1;
            for (int i = 0; i < MAX_ENB; i++) {
                if(connected_ue_array[i] == 1){
                if (ue_finished[i] == 0 && current_round_ue[i] == 0) {
                    all_finished = 0;
                    //  printf("UE %d did not finish in %d \n", i, check_times);
                } else {
                    // printf("UE %d finished check times %d\n", i, check_times);
                    ue_finished[i] = 0;
                    current_round_ue[i] = 1;
                }
              }
            }
            if (all_finished) {
                // printf("All UE finished in time \n");
                really_finished_ue = 1;
                break;
            }
            usleep(5);
        }

//        if (check_times == -1 ) {
    //         printf("Some UE did not finish in time \n");
    //    }
        check_times = 10000000;
        while (check_times--) {
            int all_finished = 1;
            for (int i = 0; i < MAX_ENB; i++) {
                if(connected_gnb_array[i] == 1){
                //  printf("Checking gnb %d\n", i);
                if (gnb_finished[i] == 0 && current_round_enb[i] == 0) {
                    all_finished = 0;
                    //  printf("gnb %d did not finish in %d \n", i, check_times);
                } else {
                    //  printf("gnb%d finished check times %d\n", i, check_times);
                    gnb_finished[i] = 0;
                    current_round_enb[i] = 1;
                }
              }
            }
            if (all_finished) {
                // printf("All enb finished in time \n");
                really_finished_gnb = 1;
                break;
            }
            usleep(5);
        }

        if (0) { // set to 1 to see logs
            if (! really_finished_ue) {
                printf("A UE did not finish on time\n");
            }
            if (! really_finished_gnb) {
                printf("A gNB did not finish on time\n");
            }
        }

        slot_checker_ack_t ack;
        ack.type = (uint8_t) TYPE_PROXY;
        ack.id = (uint32_t) args->proxy_id;
        ack.slot = (uint8_t) 0; // placeholder, don't need to send the slot number
        int send_res = sendto(sock, &ack, sizeof(ack), 0, (struct sockaddr *) &global_sc_addr, sizeof(global_sc_addr));
        assert(send_res == sizeof(ack));

        uint8_t rec_buf[100];
        int rec_res = recv(sock, rec_buf, sizeof(rec_buf), 0);
        assert(rec_res == sizeof(uint8_t));

        g_all_acks_received = 1;
        while (g_all_acks_received == 1) {
            usleep(20);
        }
    }

}
volatile sig_atomic_t terminate_requested = 0;

void handle_signal(int signum) {
    terminate_requested = 1;
    fprintf(stderr, "\nSignal %d received. Cleaning up...\n", signum);
    alarm(5);  // failsafe: kill if cleanup takes too long
}

int create_slot_checker_thread(int proxy_id, const char * proxy_ip_addr, const char * global_sc_ip_addr) {
    // setup the thread attributes so the thread terminates when complete
	// this requires seting the detach state to DETACHED, rather than the
	// default value of JOINABLE
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    signal(SIGQUIT, handle_signal);
    printf("Creating slot checker thread\n");
	pthread_attr_t thread_attr;
	assert(pthread_attr_init(&thread_attr) == 0);
	assert(pthread_attr_setdetachstate(&thread_attr, PTHREAD_CREATE_DETACHED) == 0);
    // ip list ["11.0.0.5", "11,0.0.2"];
    //char *ip_list[] = {"11.0.0.7", "11.0.0.2"};
    main_loop_args_t * args = calloc(1, sizeof(main_loop_args_t));
    args->proxy_id = proxy_id;
    args->proxy_ip = (char *) proxy_ip_addr;
    args->global_sc_ip = (char *) global_sc_ip_addr;
    g_all_acks_received = 0;
    for(int i=0;i<MAX_UES;i++){
        ue_finished[i] = 0;
        connected_ue_array[i] = 0;
    }
    for (int i = 0; i <MAX_ENB; i++)
    {
        gnb_finished[i] = 0;
        connected_gnb_array[i] = 0;
    }
    pthread_t thread;
    assert(pthread_create(&thread, &thread_attr, main_loop, (void *) args) == 0);

    return 0;
}
