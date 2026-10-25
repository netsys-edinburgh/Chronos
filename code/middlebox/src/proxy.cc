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
#include <fstream>
#include <sys/resource.h>
#include "proxy.h"
#include "lte_proxy.h"
#include "nr_proxy.h"
#include "nfapi_pnf.h"
extern "C"
{
    int num_ues = 1;
    int num_gnb = 1;
}

uint32_t proxy_ip_addr = INADDR_ANY;

static void show_usage();
static bool is_numeric(const std::string&);
static void remove_log_file();
static bool is_ipaddress(const std::string &);
static std::vector<std::string> parse_enb_ips(std::string filename);
std::vector<int> parse_enb_ids(std::string filename);
constexpr int DEFAULT_MAX_SECONDS = 100 * 60; // maximum run time

static const char *program_name;

static void die(const std::string& msg)
{
    std::clog << program_name << ": " << msg << std::endl;
    exit(EXIT_FAILURE);
}

static void try_help(const std::string& msg)
{
    die(msg + " (try --help)");
}

int main(int argc, char *argv[])
{
    // disable buffering so the logs appear when run in systemd
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);

    program_name = basename(argv[0]);

    int ues = 1;
    int max_seconds = DEFAULT_MAX_SECONDS;
    std::string filepath;
    std::string gnb_id_filepath;
    int proxy_id = 0;
    softmodem_mode_t softmodem_mode = SOFTMODEM_LTE;
    std::vector<std::string> ipaddrs;
    std::vector<std::string> enb_ipaddrs;
    std::vector<std::string> gnb_ipaddrs;
    std::vector<int> gnb_ids;
    std::vector<std::string> component_ipaddrs;

    while (--argc > 0)
    {
        std::string arg{*++argv};
        if (arg == "--help")
        {
            show_usage();
            return EXIT_SUCCESS;
        }
        if (is_numeric(arg))
        {
            ues = std::stoi(arg);
            if (ues < 1)
            {
                die("invalid number of UEs");
            }
            continue;
        }
        if (arg == "--lte")
        {
            softmodem_mode = SOFTMODEM_LTE;
            continue;
        }
        if (arg == "--nr")
        {
            softmodem_mode = SOFTMODEM_NR;
            continue;
        }
        if (arg == "--nr_n_gnb")
        {
            softmodem_mode = SOFTMODEM_NR_N_GNB;
            filepath = *++argv;
            --argc;
            continue;
        }
        if (arg == "--chronos5g")
        {
            softmodem_mode = CHRONOS_5G;
            filepath = *++argv;
            --argc;
            gnb_id_filepath = *++argv;
            --argc;
            proxy_id = atoi(*++argv);
			--argc;
            continue;
        }

        if (arg == "--nsa")
        {
            softmodem_mode = SOFTMODEM_NSA;
            continue;
        }
        if (arg == "--max-seconds")
        {
            if (--argc == 0 || !is_numeric(*++argv))
            {
                try_help("Expected an integer after --max-seconds");
            }
            max_seconds = std::stoi(*argv);
            continue;
        }
        if (is_ipaddress(arg))
        {
            ipaddrs.push_back(arg);
            continue;
        }
        try_help("unexpected argument: " + arg);
    }

    std::string ue_ip;
    std::vector<std::string> ue_ipaddr;
    std::string enb_ipaddr = "127.0.0.1";
    std::string gnb_ipaddr = "127.0.0.2";
    std::string proxy_ipaddr = "127.0.0.1";
    std::string global_slotchecker_ip = "127.0.0.1";
    switch (ipaddrs.size())
    {
    case 0:
        if (softmodem_mode == SOFTMODEM_NR_N_GNB)
            {
                enb_ipaddrs.push_back("127.0.0.1");
                enb_ipaddrs.push_back("127.0.0.2");
            }
            else
                enb_ipaddrs.push_back("127.0.0.1");
            break;
       break; // If using the default set IP addresses: resize the vector size to match number of UEs
    case 1:
        if (softmodem_mode == SOFTMODEM_NR_N_GNB)
            {
                gnb_ipaddrs = parse_enb_ips(filepath);
                proxy_ipaddr = ipaddrs[0];
                std::cout << "Using GNB IPs: ";
                for (const auto& ip : gnb_ipaddrs) {
                    std::cout << ip << " "; }
            }
            break;
    case 2:
        if (softmodem_mode == CHRONOS_5G)
            {
                gnb_ipaddrs = parse_enb_ips(filepath);
                gnb_ids = parse_enb_ids(gnb_id_filepath); // TODO
                proxy_ipaddr = ipaddrs[0];
                proxy_ip_addr = inet_addr(proxy_ipaddr.c_str()); // to be used later to bind() to
                global_slotchecker_ip = ipaddrs[1];
                std::cout << "Proxy ID: " << proxy_id << "\n";
                std::cout << "Global SlotChecker IP: " << global_slotchecker_ip << "\n";
                std::cout << "Using GNB IPs: ";
                for (const auto& ip : gnb_ipaddrs) {
                    std::cout << ip << " "; }
            }
        break;
    case 3:
        if (softmodem_mode == SOFTMODEM_NSA) // NSA mode needs at least 4 IP addrs
        {
            try_help("Wrong number of IP addresses");
        }
        enb_ipaddr = ipaddrs[0];
        gnb_ipaddr = ipaddrs[0];
        proxy_ipaddr = ipaddrs[1];
        ue_ipaddr.push_back(ipaddrs[2]);
        break;
    case 4:
        if (softmodem_mode == SOFTMODEM_NSA)
        {
            enb_ipaddr = ipaddrs[0];
            gnb_ipaddr = ipaddrs[1];
            proxy_ipaddr = ipaddrs[2];
            ue_ipaddr.push_back(ipaddrs[3]);
        } else if (ues == 2) {
            enb_ipaddr = ipaddrs[0];
            gnb_ipaddr = ipaddrs[0];
            proxy_ipaddr = ipaddrs[1];
            ue_ipaddr.push_back(ipaddrs[2]);
            ue_ipaddr.push_back(ipaddrs[3]);
        } else {
            try_help("Wrong number of IP addresses");
        }
        break;
    default: // Only catches 5+ IP addresses
        try_help("Invalid number of IP addresses");
        break;
    }

    remove_log_file();

    /* This alarm is important because we run with the real-time scheduler.
       If (due to bugs) this process were to become run-away (running
       continuously without ever blocking), the alarm will eventually kill the
       process.  Otherwise, the host machine would need to be rebooted */
    std::clog << "max_seconds: " << max_seconds << std::endl;
    //alarm(max_seconds);

    /* Enable core dumps */
    {
        struct rlimit lim = { RLIM_INFINITY, RLIM_INFINITY };
        if (setrlimit(RLIMIT_CORE, &lim) == -1)
            std::clog << program_name << ": setrlimit: " << strerror(errno) << '\n';
    }

    switch (softmodem_mode)
    {
    case SOFTMODEM_LTE:
        {
            Multi_UE_Proxy lte_proxy(ues, enb_ipaddr, proxy_ipaddr, ue_ipaddr);
            lte_proxy.start(softmodem_mode);
        }
        break;
    case SOFTMODEM_NR:
        {
            //Multi_UE_NR_Proxy nr_proxy(ues, gnb_ipaddrs, proxy_ipaddr, ue_ip);
			//TODO Add ACK senders
			Multi_UE_NR_Proxy nr_proxy(ues, gnb_ipaddrs, proxy_ipaddr, ue_ip);
            nr_proxy.start(softmodem_mode);
        }
        break;
    case SOFTMODEM_NSA:
        {
            Multi_UE_Proxy lte_proxy(ues, enb_ipaddr, proxy_ipaddr, ue_ipaddr);
            //Multi_UE_NR_Proxy nr_proxy(ues, gnb_ipaddrs, proxy_ipaddr, ue_ip);
            //TODO Add ACK senders
			Multi_UE_NR_Proxy nr_proxy(ues, gnb_ipaddrs, proxy_ipaddr, ue_ip);

            std::thread lte_th( &Multi_UE_Proxy::start, &lte_proxy, softmodem_mode);
            std::thread nr_th( &Multi_UE_NR_Proxy::start, &nr_proxy, softmodem_mode);

            lte_th.join();
            nr_th.join();
        }
        break;
    case SOFTMODEM_NR_N_GNB:
        {
            printf("Starting NR Proxy with %d UEs\n", ues);
            //Multi_UE_NR_Proxy nr_proxy(ues, gnb_ipaddrs, proxy_ipaddr, ue_ip);
			//TODO Add ACK senders
			Multi_UE_NR_Proxy nr_proxy(ues, gnb_ipaddrs, proxy_ipaddr, ue_ip);
            nr_proxy.start(softmodem_mode);
        }
        break;
    case CHRONOS_5G:
        {
            printf("Starting NR Proxy with %d UEs\n", ues);
            //Multi_UE_NR_Proxy nr_proxy(ues, gnb_ipaddrs, proxy_ipaddr, ue_ip);
			//TODO Add ACK senders
			Multi_UE_NR_Proxy nr_proxy(ues, gnb_ipaddrs, gnb_ids, proxy_ipaddr, proxy_id, global_slotchecker_ip, ue_ip);
            nr_proxy.start(softmodem_mode);
        }
            break;
    default:
        abort();
    }
    return EXIT_SUCCESS;
}

void show_usage()
{
    std::cout << "usage: " << program_name << " [options] num_UEs [IP addresses]\n"
              << "  num_UEs   Number of UE instances (default: 1)\n"
              << "  Number of IP address:\n"
              << "    0 - use the loopback interface (default)\n"
              << "    1 - GNB proxy UE (for NR modes)\n"
              << "    3 - ENB/GNB proxy UE (for LTE and NR modes)\n"
              << "    4 - ENB GNB proxy UE (for NSA mode)\n"
              << "  Options:\n"
              << "    --lte              Softmodem mode is LTE (default)\n"
              << "    --nr               Softmodem mode is NR\n"
              << "    --nsa              Softmodem mode is NSA\n"
              << "    --nr_n_gnb         Softmodem mode is NR N GNB\n"
              << "    --max-seconds SEC  Maximum run time (default: " << DEFAULT_MAX_SECONDS << ")\n";
}

bool is_numeric(const std::string &s)
{
    for (char c: s)
    {
        if (!isdigit((unsigned char) c))
        {
            return false;
        }
    }
    return true;
}

void remove_log_file()
{
    static const char log_name[] = "nfapi.log";
    if (remove(log_name) != 0 && errno != ENOENT)
    {
        std::clog << program_name << ": remove " << log_name
                  << ": " << strerror(errno) << std::endl;
    }
}

bool is_ipaddress(const std::string &s)
{
    sockaddr_in sa;
    return 1 == inet_pton(AF_INET, s.c_str(), &sa.sin_addr);
}

std::vector<std::string> parse_enb_ips(std::string filename)
{
    std::ifstream ips_file(filename);
    std::string line;
    std::vector<std::string> enb_ips;

    if (!ips_file.good()) {
        std::cout << "Failed to open " << filename << ", file might not exist";
        abort();
    }

    while (std::getline(ips_file, line))
    {
        if (is_ipaddress(line))
        {
            std::cout << "Valid IP: " << line << "\n";
            enb_ips.push_back(line);
        } else {
            std::cout << "Invalid IP: " << line << "\n";
        }
    }
    ips_file.close();

    return enb_ips;
}

std::vector<int> parse_enb_ids(std::string filename)
{
    std::ifstream ids_file(filename);
    std::string line;
    std::vector<int> enb_ids;

    if (!ids_file.good()) {
        std::cout << "Failed to open " << filename << ", file might not exist";
        abort();
    }
    while (std::getline(ids_file, line))
    {
        int id = atoi(line.c_str());
        std::cout << "Read gNB ID: " << id << "\n";
        enb_ids.push_back(id);
    }
    ids_file.close();

    return enb_ids;
}