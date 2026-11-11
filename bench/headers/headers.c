/* Equivalent array-header kernels; build with cc -O2 (no restrict assumptions). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static double *ga, *gb, *gc;
static long *gx, *gh;
#define MATRIX(a,b,c,n) \
    for(long r=0;r<8;r++) for(long i=0;i<n;i++) \
        for(long j=0;j<n;j++) for(long k=0;k<n;k++) \
            c[i*n+j] += a[i*n+k]*b[k*n+j]
#define STENCIL(c,n) \
    for(long r=0;r<32;r++) for(long i=1;i<n-1;i++) \
        c[i]=(c[i-1]+c[i]+c[i+1])*0.25
#define HISTOGRAM(x,h,n) \
    for(long r=0;r<8;r++) for(long i=0;i<n;i++) h[x[i]]++
static double *fill(double v,long n) {
    double *p=malloc(n*sizeof *p);
    for(long i=0;i<n;i++) p[i]=v;
    return p;
}
static long *indices(long n) {
    long *p=malloc(n*sizeof *p);
    for(long i=0;i<n;i++) p[i]=i%256;
    return p;
}
__attribute__((noinline)) static void matrix_param(double *a,double *b,double *c,long n) { MATRIX(a,b,c,n); }
__attribute__((noinline)) static void stencil_param(double *c,long n) { STENCIL(c,n); }
__attribute__((noinline)) static void histogram_param(long *x,long *h,long n) { HISTOGRAM(x,h,n); }
__attribute__((noinline)) static double matrix_local(long n) {
    double *a=fill(1,n*n),*b=fill(0.5,n*n),*c=fill(0,n*n);
    MATRIX(a,b,c,n);
    double result=c[n*n-1]; free(a);free(b);free(c); return result;
}
__attribute__((noinline)) static double stencil_local(long n) {
    double *c=fill(1,n); STENCIL(c,n);
    double result=c[n/2];free(c);return result;
}
__attribute__((noinline)) static long histogram_local(long n) {
    long *x=indices(n),*h=calloc(256,sizeof *h); HISTOGRAM(x,h,n);
    long result=h[17];free(x);free(h);return result;
}
__attribute__((noinline)) static void matrix_global(long n) { MATRIX(ga,gb,gc,n); }
__attribute__((noinline)) static void stencil_global(long n) { STENCIL(gc,n); }
__attribute__((noinline)) static void histogram_global(long n) { HISTOGRAM(gx,gh,n); }
int main(int argc,char **argv) {
    const char *mode=argv[1];long n=64+argc-2;
    if(!strncmp(mode,"matrix",6)) {
        if(!strcmp(mode,"matrix_local")) printf("%g\n",matrix_local(n));
        else {ga=fill(1,n*n);gb=fill(0.5,n*n);gc=fill(0,n*n);
            if(!strcmp(mode,"matrix_param")) matrix_param(ga,gb,gc,n);else matrix_global(n);
            printf("%g\n",gc[n*n-1]);}
    } else if(!strncmp(mode,"stencil",7)) {
        n*=1024;
        if(!strcmp(mode,"stencil_local")) printf("%.12g\n",stencil_local(n));
        else {gc=fill(1,n);
            if(!strcmp(mode,"stencil_param")) stencil_param(gc,n);else stencil_global(n);
            printf("%.12g\n",gc[n/2]);}
    } else {
        n*=4096;
        if(!strcmp(mode,"histogram_local")) printf("%ld\n",histogram_local(n));
        else {gx=indices(n);gh=calloc(256,sizeof *gh);
            if(!strcmp(mode,"histogram_param")) histogram_param(gx,gh,n);else histogram_global(n);
            printf("%ld\n",gh[17]);}
    }
}
