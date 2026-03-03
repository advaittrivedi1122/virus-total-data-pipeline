# Architecture :

```
Incoming Request
       │
       V
 Redis Cache ──── HIT ──────────────────> Return (source: cache)
       │
      MISS
       │
       V
  PostgreSQL ──── HIT ──────────────────> Repopulate Cache ► Return (source: db)
       │
      MISS
       │
       V
 VirusTotal API
       │
       V
 Parse & Store ──> Write to DB + Cache ──> Return (source: virustotal)
```