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
#include <errno.h>
#include <sys/time.h>

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

    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 300000;
    if (setsockopt(sock_udp, SOL_SOCKET, SO_RCVTIMEO,&tv,sizeof(tv)) < 0) {
        perror("Error");
    }

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

uint8_t gslot;
int timeout_round;
uint8_t proxy_acks[MAX_PROXY];
uint8_t component_acks[MAX_PROXY];

void timeout_mitigation() {
    // log the components responsible for the timeout
    printf("Timedout %u waiting for socket\n", timeout_round);
    printf("Still waiting for components: ");
    for (int i = 0; i < MAX_COMPONENT; i++)
        if (components[i] == STATE_ACTIVE && ! component_acks[i])
            printf("%u ", i);
    printf("\n");
    printf("Still waiting for proxies: ");
    for (int i = 0; i < MAX_PROXY; i++)
        if (proxies[i] == STATE_ACTIVE && ! proxy_acks[i])
            printf("%u ", i);
    printf("\n");

    // perform the timeout mitigation
    switch(timeout_round) {
        case 1:
        case 2:
        case 3:
            ; // The first three timeout rounds, ignore
            break;
        case 4:
        case 5:
        case 6:
            ; // Next three timeout round, try sending slot again
            for (int i = 0; i < MAX_PROXY; i++) {
                if (proxies[i] == STATE_ACTIVE && ! proxy_acks[i]) {
                    int res = send(proxy_socks[i], &gslot, sizeof(gslot), 0);
                    if (res != sizeof(gslot)) {
                        printf("Failed to resend slot to proxy %d\n", i);
                        printf("Assuming it has crashed, so marking it as not connected\n");
                        proxies[i] = 0;
                    }
                }
            }
        default:
            ; // last-ditch approach: mark the proxies as not connected
            for (int i = 0; i < MAX_PROXY; i++)
                if (proxies[i] == STATE_ACTIVE && ! proxy_acks[i])
                    proxies[i] = 0;

    }

    // increment the timeout counter
    timeout_round++;
}

int get_all_acks(int sock, uint8_t * proxies, uint8_t * components) {
    bzero(&proxy_acks, sizeof(proxy_acks));
    bzero(&component_acks, sizeof(component_acks));

    timeout_round = 0;
    
    while (1) {
        // check to see if we have received all the acks from proxies
        uint8_t found_all_proxy_ack = 1;
        for (int i = 0; i < MAX_PROXY; i++) {
            // first check is if proxy is connected, second check is if proxy has acked for this slot
            if (proxies[i] == STATE_ACTIVE && ! proxy_acks[i]) {
                found_all_proxy_ack = 0;
                break;
            }
        }

        // check to see if we have received all the acks from components
        uint8_t found_all_component_ack = 1;
        for (int i = 0; i < MAX_COMPONENT; i++) {
            // first check is if component is connected, second check is if component has acked for this slot
            if (components[i] == STATE_ACTIVE && ! component_acks[i]) {
                found_all_component_ack = 0;
                break;
            }
        }

        if (found_all_proxy_ack && found_all_component_ack) {
            break;
        }
        

        // if we reach here then we are still waiting for at least one ack
        slot_checker_ack_t ack;
        struct sockaddr_in client_addr;
        socklen_t from_len = sizeof(client_addr);
        memset(&client_addr, 0, sizeof(client_addr));
        int n = recvfrom(sock, &ack, sizeof(ack), 0, (struct sockaddr *) &client_addr, &from_len);

        // check ack length is correct
        if (n != sizeof(ack) && errno == EAGAIN) {
            timeout_mitigation();
            continue;
        }
        else if (n != sizeof(ack)) {
            printf("Error, received message of size %d (expected %lu)\n", n, sizeof(ack));
            continue;
        }

        // check the type is valid
        if (ack.type != TYPE_PROXY && ack.type != TYPE_COMPONENT) {
            printf("Error, unknown component type %u\n", ack.type);
            return 1;
        }

        // check this ack is within range
        if (ack.type == TYPE_PROXY && ack.id >= MAX_PROXY) {
            printf("Error, proxy ack %u outside of range (0-%u)\n", ack.id, MAX_PROXY);
            return 1;
        }
        if (ack.type == TYPE_COMPONENT && ack.id >= MAX_COMPONENT) {
            printf("Error, component ack %u outside of range (0-%u)\n", ack.id, MAX_COMPONENT);
            return 1;
        }

        // check for a new proxy connecting
        if (ack.type == TYPE_PROXY && proxies[ack.id] == 0) {
            printf("New proxy connected: ID %u, IP %s:%u\n", ack.id, inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));
            proxy_socks[ack.id] = udp_socket_open(create_address(global_sc_ip, 0));
            udp_socket_connect(proxy_socks[ack.id], create_address(inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port)));
            proxies[ack.id] = 1;
        }

        // check for ack from unconnected component
        if (ack.type == TYPE_COMPONENT && components[ack.id] == 0) {
            printf("Error, ack from component %u but it never connected\n", ack.id);
            return 1;
        }

        // check we haven't received this ack before
        if (ack.type == TYPE_PROXY && proxy_acks[ack.id] == 1) {
            printf("Error, duplicate ack received for proxy %u\n", ack.id);
            return 1;
        }
        if (ack.type == TYPE_COMPONENT && component_acks[ack.id] == 1) {
            printf("Error, duplicate ack received for component %u\n", ack.id);
            return 1;
        }

        // store the ack
        if (ack.type == TYPE_PROXY) {
            proxy_acks[ack.id] = 1;
        }
        if (ack.type == TYPE_COMPONENT) {
            component_acks[ack.id] = 1;
        }
    }

    return 0;
}

void read_in_components(char * component_file) {
    FILE *fptr = fopen(component_file, "r");
    
    char component_ip_str[100];
    // Read data of file in specific format
    while (fscanf(fptr, "%s", component_ip_str) == 1) {
        int current_component = (uint8_t) ((inet_addr(component_ip_str) >> 16) & 0xFF) - 1  ;
        printf("Component %d is at IP %s\n", current_component, component_ip_str);
        components[current_component] = STATE_ACTIVE; // make first component only active
        component_socks[current_component] = udp_socket_open(create_address(global_sc_ip, 0));
        udp_socket_connect(component_socks[current_component], create_address(component_ip_str, 4322));
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

int main(int argc, char ** argv) {
    int slowdown = 0;
    int iterations = 0;
    struct timeval start, stop;

    // disable buffering so the logs appear when run in systemd
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);

    if (argc != 3) {
        printf("Usage: ./slotchecker <Slotchecker IP> <Component IP File>\n");
        return 1;
    }

    // initialise state
    memset(proxies, 0, sizeof(proxies));
    memset(components, 0, sizeof(components));

    read_in_components(argv[2]);

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    signal(SIGQUIT, handle_signal);

    strcpy(global_sc_ip, argv[1]); // TODO: security risk
    printf("Running global slot checker on %s:%u\n", global_sc_ip, GLOBAL_SC_RX_PORT);
    int sock = udp_socket_open(create_address(global_sc_ip, GLOBAL_SC_RX_PORT));

    // start things running
    uint8_t start_signal = 1;
    for (int i = 0; i < MAX_COMPONENT; i++) {
        if (! components[i])
            continue;
        printf("Starting component %d\n", i);
        int t = send(component_socks[i], &start_signal, sizeof(start_signal), 0);
        assert(t == sizeof(start_signal));
    }


    gslot = 2;

    while (1) {
        // get all the ACKs from the current slot
        int res = get_all_acks(sock, proxies, components);
        assert(res >= 0);

        // in slowdown mode, wait for 100ms before sending new slot
        if (slowdown)
            usleep(100000);

        // send the new slot to all components
        for (int i = 0; i < MAX_COMPONENT; i++) {
            if (! components[i])
                continue;
            res = send(component_socks[i], &gslot, sizeof(gslot), 0);
            assert(res == sizeof(gslot));
        }

        // send the new slot to all proxies
        for (int i = 0; i < MAX_PROXY; i++) {
            if (! proxies[i])
                continue;
            res = send(proxy_socks[i], &gslot, sizeof(gslot), 0);
            if (res != sizeof(gslot)) {
                printf("Failed to send new slot to proxy %d\n", i);
                printf("Assuming it has crashed, so marking it as not connected\n");
                proxies[i] = 0;
            }
        }

        // increment the slot
        gslot++;

        // slot IDs 0 and 1 are reserved for special purposes
        if(gslot==0) {
            gslot=2;
            // check if we want deliberate slowdown
            if (access("/slowdown", F_OK) == 0 && slowdown == 0) {
                printf("Slowdown mode enabled\n");
                slowdown = 1;
            }
        }

        // check if we want to stop the slowdown
        if (slowdown == 1 && access("/slowdown", F_OK) != 0) {
            printf("Slowdown mode disabled\n");
            slowdown = 0;
        }

        if (iterations >= 1000) {
            // report the current dilation factor
            gettimeofday(&stop, NULL);
            uint64_t elapsed = (stop.tv_sec - start.tv_sec) * 1e6 + (stop.tv_usec - start.tv_usec);
            float dilationf = elapsed / 1e6;
            printf("Elapsed: %lu, Dilation factor: %.2f\n", elapsed, dilationf);
            iterations = 0;
        }

        if (iterations == 0) {
            // start time for next 1000 slots
            gettimeofday(&start, NULL);
        }

        iterations ++;
    }
}
