#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include "stdint.h"
#define MAX_ENB 950  
#define MAX_UES 2000
typedef struct {
    int proxy_id;
    char * proxy_ip;
    char * global_sc_ip;
} main_loop_args_t;

#define TYPE_PROXY 1
#define TYPE_COMPONENT 2
typedef struct __attribute__((__packed__)) slot_checker_ack {
    uint8_t type;
    uint32_t id;
    uint8_t slot;
} slot_checker_ack_t;


int received_all_acks(uint8_t * acks, uint16_t num_ues_enbs);

int get_all_acks(int sock, uint16_t num_ues_enbs);

void * main_loop(void * raw_args);

int create_slot_checker_thread(int proxy_id, const char * proxy_ip_addr, const char * global_sc_ip_addr);
int send_slot_start(uint8_t num_to_send);


#ifdef __cplusplus
}
#endif