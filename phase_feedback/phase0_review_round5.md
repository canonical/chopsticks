# Phase 0 Review – Round 5 Findings

## Summary
- High severity: 1

## Findings
1. **High – SSH reachability probe fails on stock Ubuntu due to MOTD output.** The new SSH transport checks for an exact `"reachable"` string after running `ssh … echo reachable`, but Ubuntu’s MOTD subsystem prints banner lines to stdout for every login. That makes `result.stdout.strip()` contain multiple lines (welcome text + reachable), so the equality test fails even though the connection succeeded. As a result, every default MicroCeph node reports “SSH handshake failed” and the pre-flight exits non-zero. Evidence: [roadmap.md](roadmap.md#L5-L8), [src/chopsticks/utils/ssh.py](src/chopsticks/utils/ssh.py#L83-L128). *Recommendation:* look for the marker within the output (e.g., `if "reachable" in result.stdout`) or redirect MOTD output (e.g., run `ssh … "printf reachable"` and capture only stdout) so legitimate SSH sessions aren’t flagged as failures.
