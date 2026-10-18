#include "recorder_storage.h"
#include "recorder_core.h"
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

int ohmni_new_file(const char *directory, char *path, size_t length) {
    for (unsigned n=1;n<=99999;n++) {
        char finished[512];
        int used=snprintf(finished,sizeof(finished),"%s/REC%05u.wav",directory,n);
        if(used<0 || (size_t)used>=sizeof(finished)) return -1;
        if(access(finished,F_OK)==0) continue;
        used=snprintf(path,length,"%s/REC%05u.tmp",directory,n);
        if(used<0 || (size_t)used>=length) return -1;
        int fd=open(path,O_CREAT|O_EXCL|O_RDWR,0666);
        if(fd>=0) return fd;
        if(errno!=EEXIST) break;
    }
    return -1;
}
bool ohmni_write_all(int fd,const void *data,size_t size) {
    const uint8_t *p=data;
    while(size) {
        ssize_t n=write(fd,p,size);
        if(n<0 && errno==EINTR) continue;
        if(n<=0) return false;
        p+=n;size-=(size_t)n;
    }
    return true;
}
bool ohmni_finish_file(int fd,const char *path,uint32_t rate,uint32_t bytes,bool capture_ok) {
    uint8_t header[44];ohmni_wav_header(header,rate,bytes);
    bool ok=capture_ok;
    if(lseek(fd,0,SEEK_SET)<0 || !ohmni_write_all(fd,header,44) || fsync(fd)!=0) ok=false;
    if(close(fd)!=0) ok=false;
    if(!ok) return false;
    char finished[512];size_t size=strlen(path);
    if(size<4 || size>=sizeof(finished) || strcmp(path+size-4,".tmp")!=0) return false;
    memcpy(finished,path,size+1);memcpy(finished+size-3,"wav",3);
    /* The recorder is the sole writer; also preserve a file created meanwhile. */
    if(access(finished,F_OK)==0) return false;
    return rename(path,finished)==0;
}
