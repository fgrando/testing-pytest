#include <stdio.h>

/* Stand-in for a first-stage bootloader image.
 * In a real K3/Jacinto build this would be the R5 SPL; here it is just
 * a binary to exercise the build + sign + archive pipeline end to end. */
int main(void)
{
    printf("dummy first-stage bootloader image\n");
    return 0;
}
