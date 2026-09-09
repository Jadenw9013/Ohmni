# KiCad native failures on Windows

On 2026-09-09, local test runs launched from the restricted coding environment
triggered repeated `kicad-cli.exe - Application Error` dialogs. The screenshot
showed a null instruction address and a failed memory write. The three affected
API tests stopped before producing an ERC report; they were not successful
board builds. No KiCad or WerFault processes remained at process inspection.

The same KiCad executable (`10.0.5`) timed out on a guarded eight-second version
probe in that restricted environment, then returned version `10.0.5` and exit
zero in normal execution. This points to environment-dependent initialization;
it does not identify the native faulting module. No matching Windows Application
event was available. A retained sandbox artifact also had an ACL that prevented
the normal execution user from reading it. Cross-environment artifact reuse
therefore produced “Failed to load schematic” and cannot serve as a retest.

Run real KiCad verification with normal filesystem access and a fresh output
directory created by the same execution identity. Do not repeatedly retry native
EDA under a restricted identity after initialization fails. Do not change global
Windows Error Reporting, KiCad preferences, DLLs or registry settings to make a
failed check appear to pass.

Ohmni's native-tool runner gives Windows children a noninteractive error mode,
captures stdout/stderr and enforces the timeout. The previous parent mode is
restored, and native exit codes remain failures. This follows Microsoft's
[documented child-process error-mode inheritance](https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-seterrormode).
The safeguard prevents OS crash dialogs from blocking automated jobs; it is not
a repair for KiCad itself and cannot suppress arbitrary dialogs created by a
tool's own code.

ERC/DRC must reject unexpected exit codes and cannot accept a prior report left
over from another run. A failed export must not create a release manifest.
Focused regression tests exercise these boundaries without deliberately crashing
a native application.
