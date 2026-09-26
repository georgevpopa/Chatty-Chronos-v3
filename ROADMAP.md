# 🗺️ Roadmap Chatty-Chronos-v2 (Next-Gen)

Următoarele funcționalități vor transforma Chronos dintr-un simplu agent CLI într-o platformă vizuală și arhitecturală de top:

| Prioritate | Direcție | Funcționalitate & Implementare |
| :--- | :--- | :--- |
| **P1** | **Architecture** | **Streaming de Tool Execution:** Trecerea de la procesare "blocantă" (unde așteptăm 30 de pași) la **Server-Sent Events (SSE)** sau WebSockets în `ui/web.py`. Utilizatorul va vedea în timp real (litera cu literă) ce gândește agentul, ce tool apelează și cum arată output-ul parțial. |
| **P2** | **UX** | **Inline Diff View:** Când agentul vrea să modifice un cod, înainte să facă `write_file`, se trimite un semnal de "Approval" către dashboard. UI-ul va randa un block *side-by-side* roșu/verde (tip GitHub) ca utilizatorul să vadă exact ce linii se șterg/adaugă. |
| **P3** | **Memory** | **Hierarchical Memory:** Integrarea *ChromaDB* (deja adăugat în docker-compose). Sesiunea curentă rămâne în contextul imediat, dar rezumatele task-urilor trecute sunt vectorizate. Când agentul primește un task nou, caută similarități în ChromaDB ("am mai rezolvat asta luna trecută?"). |
| **P4** | **AI Quality** | **Self-Reflection Loop:** Un "Reviewer Agent" separat. Când agentul principal zice "Task completed", reviewer-ul citește task-ul inițial, rezultatul final, inspectează fișierele și dă un scor. Dacă e sub 8/10, întoarce agentul la muncă cu un set clar de critici. |
| **P5** | **MCP** | **MCP Registry UI:** Interfață vizuală în dashboard (un fel de App Store) unde aplicația citește toate uneltele `mcp_tool` disponibile pe sistem și permite activarea/dezactivarea lor cu un singur click. |

---
*Acest document va fi folosit ca referință pentru următoarele noastre acțiuni.*
