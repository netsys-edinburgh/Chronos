//#include "sc_global.h"

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
#include <time.h>

#define GLOBAL_SC_RX_PORT 6000

#define MAX_PROXY 100
#define MAX_COMPONENT 100

#define STATE_ACTIVE 1

#define TYPE_PROXY 1
#define TYPE_COMPONENT 2
typedef struct __attribute__((__packed__)) slot_checker_ack {
    uint8_t type;
    uint32_t id;
    uint8_t slot;
} slot_checker_ack_t;

char global_sc_ip[100];
int proxy_socks[MAX_PROXY];
int component_socks[MAX_COMPONENT];
volatile sig_atomic_t terminate_requested = 0; // TODO: don't think we need this!
uint8_t proxies[MAX_PROXY];
uint8_t components[MAX_COMPONENT];

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

void read_in_components(char * component_file) {
    FILE *fptr = fopen(component_file, "r");
    
    int current_component = 0;
    char component_ip_str[100];
    // Read data of file in specific format
    while (fscanf(fptr, "%s", component_ip_str) == 1) {
        printf("Component %d is at IP %s\n", current_component, component_ip_str);
        components[current_component] = STATE_ACTIVE; // make first component only active
        component_socks[current_component] = udp_socket_open(create_address(global_sc_ip, 0));
        udp_socket_connect(component_socks[current_component], create_address(component_ip_str, 4322));
        current_component ++;
    }
    fclose(fptr);
}

void handle_signal(int signum) {
    uint8_t kill_signal = 0;
    for (int i = 0; i < MAX_COMPONENT; i++) {
        if (! components[i])
            continue;
        int t = send(component_socks[i], &kill_signal, sizeof(kill_signal), 0);
        assert(t == sizeof(kill_signal));
    }
    terminate_requested = 1;
    fprintf(stderr, "\nSignal %d received. Cleaning up...\n", signum);
    printf("Exiting sending -1 to components \n");
    alarm(5);  // failsafe: kill if cleanup takes too long
}


// Standard recursive Fibonacci implementation
unsigned long long fib(int n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

int main(int argc, char ** argv) {
    // disable buffering so the logs appear when run in systemd
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);

    if (argc != 6) {
        printf("Usage: ./slotchecker <Component IP File> <fib_start_n> <fib_end_n> <fib_step> <Dilated=1/0>\n");
        return 1;
    }

    if (atoi(argv[5])) {
        printf("Running with dilation\n");
    } else {
        printf("Running without dilation\n");
    }

    //Parse args
    char *component_file = argv[1];
    int fib_start = atoi(argv[2]);
    int fib_end = atoi(argv[3]);
    int fib_step = atoi(argv[4]);


    // initialise state
    memset(proxies, 0, sizeof(proxies));
    memset(components, 0, sizeof(components));

    read_in_components(argv[1]);

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    signal(SIGQUIT, handle_signal);

    uint8_t start_signal = 1;
    uint8_t kill_signal = 0;

    // start dilation
    if (atoi(argv[5])) {
        for (int i = 0; i < MAX_COMPONENT; i++) {
            if (! components[i])
                continue;
            printf("Starting component %d\n", i);
            int t = send(component_socks[i], &start_signal, sizeof(start_signal), 0);
            assert(t == sizeof(start_signal));
        }
    }


    struct timespec start, stop;

    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start);


    /// do something
    for (int n = fib_start; n <= fib_end; n += fib_step) {
        struct timespec start, stop;
        clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start);
        unsigned long long result = fib(n);
        clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &stop);
        uint64_t elapsed = (stop.tv_sec - start.tv_sec) * 1e9 + (stop.tv_nsec - start.tv_nsec);
    }





    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &stop);

    // stop dilation
    if (atoi(argv[5])) {
        for (int i = 0; i < MAX_COMPONENT; i++) {
            if (! components[i])
                continue;
            int t = send(component_socks[i], &kill_signal, sizeof(kill_signal), 0);
            assert(t == sizeof(kill_signal));
        }
    }

    uint64_t result = (stop.tv_sec - start.tv_sec) * 1e9 + (stop.tv_nsec - start.tv_nsec);

    printf("Elapsed time (ns): %lu\n", result);
}

