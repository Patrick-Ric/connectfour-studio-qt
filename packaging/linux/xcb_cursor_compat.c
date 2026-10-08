/* Kompatibilitaets-Shim fuer libxcb-cursor (AppImage, glibc >= 2.28).
 *
 * glibc >= 2.38 leitet strtol() bei _GNU_SOURCE auf __isoc23_strtol um
 * (Symbolversion GLIBC_2.38). Diese Datei wird OHNE _GNU_SOURCE uebersetzt
 * und stellt eine lokale (versteckte) __isoc23_strtol bereit, die das alte
 * strtol@GLIBC_2.2.5 aufruft. So laeuft die gebaute Bibliothek auch auf
 * aelteren Distributionen.
 */
#include <stdlib.h>

__attribute__((visibility("hidden")))
long __isoc23_strtol(const char *nptr, char **endptr, int base)
{
    return strtol(nptr, endptr, base);
}
