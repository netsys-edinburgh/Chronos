#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>  // Include this header for fixed-width integer types
#include <signal.h>

typedef struct {
    char *shmPath;
    void *sharedMem;
    uint64_t size;
    int mapped;
} Host;

// Function to create a new host mapper
Host* NewHost(const char *shmPath) {
    struct stat st;
    if (stat(shmPath, &st) != 0) {
        perror("stat file");
        return NULL;
    }

    Host *host = (Host *)malloc(sizeof(Host));
    if (!host) {
        perror("malloc");
        return NULL;
    }

    host->shmPath = strdup(shmPath);
    if (!host->shmPath) {
        perror("strdup");
        free(host);
        return NULL;
    }

    host->sharedMem = NULL;
    host->size = 0;
    host->mapped = 0;
    return host;
}

// Function to map the shared memory into the program memory space
int Map(Host *host) {
    int fd = open(host->shmPath, O_RDWR);
    if (fd == -1) {
        perror("open device file");
        return -1;
    }

    struct stat st;
    if (fstat(fd, &st) == -1) {
        perror("stat file");
        close(fd);
        return -1;
    }

    void *sharedMem = mmap(NULL, st.st_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (sharedMem == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return -1;
    }

    host->mapped = 1;
    host->sharedMem = sharedMem;
    host->size = st.st_size;
    close(fd);
    return 0;
}

// Function to unmap the shared memory
int Unmap(Host *host) {
    if (munmap(host->sharedMem, host->size) == -1) {
        perror("munmap");
        return -1;
    }
    host->mapped = 0;
    return 0;
}

// Function to get the size of the shared memory space
uint64_t Size(Host *host) {
    return host->size;
}

// Function to get the device path of the shared memory file
const char* DevPath(Host *host) {
    return host->shmPath;
}

// Function to return the already mapped shared memory, panics if Map() didn't succeed
void* SharedMem(Host *host) {
    if (!host->mapped) {
        fprintf(stderr, "tried to access non-mapped memory\n");
        exit(EXIT_FAILURE);
    }
    return host->sharedMem;
}

// Function to ensure the changes made to the shared memory are synced
int Sync(Host *host) {
    if (msync(host->sharedMem, host->size, MS_SYNC) == -1) {
        perror("msync");
        return -1;
    }
    return 0;
}

// Function to write data to shared memory
void WriteToSharedMem(Host *host, const char *data) {
    if (!host->mapped) {
        fprintf(stderr, "tried to write to non-mapped memory\n");
        exit(EXIT_FAILURE);
    }

    size_t data_len = strlen(data) + 1; // Include null terminator
    if (data_len > host->size) {
        fprintf(stderr, "data is too large to fit in shared memory\n");
        exit(EXIT_FAILURE);
    }

    memcpy(host->sharedMem, data, data_len);
}

// Function to read data from shared memory
void ReadFromSharedMem(Host *host, char *buffer, size_t buffer_size) {
    if (!host->mapped) {
        fprintf(stderr, "tried to read from non-mapped memory\n");
        exit(EXIT_FAILURE);
    }

    size_t data_len = strnlen((char*)host->sharedMem, host->size);
    if (data_len >= buffer_size) {
        fprintf(stderr, "buffer is too small to hold the data\n");
        exit(EXIT_FAILURE);
    }

    memcpy(buffer, host->sharedMem, data_len);
    buffer[data_len] = '\0'; // Null terminate the buffer
}
volatile sig_atomic_t stop = 0;

void handle_sigint(int sig) {
    stop = 1;
}

int main() {
    const char *shmPath = "/dev/shm/my-little-shared-memory";
    Host *host = NewHost(shmPath);

    if (!host) {
        return 1;
    }

    if (Map(host) != 0) {
        free(host);
        return 1;
    }
    signal(SIGINT, handle_sigint);

    char buffer[256]; 
    while (!stop) {
        ReadFromSharedMem(host, buffer, sizeof(buffer));
        printf("Read from shared memory: %s\n", buffer);
//        WriteToSharedMem(host,"S");
        usleep(10); // Add a small delay to reduce CPU usage
    }

    if (Sync(host) != 0) {
        fprintf(stderr, "Failed to sync memory\n");
    }

    if (Unmap(host) != 0) {
        fprintf(stderr, "Failed to unmap memory\n");
    }

    free(host->shmPath);
    free(host);

    return 0;
}
