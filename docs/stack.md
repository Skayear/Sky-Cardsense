# Stack tecnológico

Tecnologías previstas para Sky-Cardsense, organizadas por componente. Ver [`architecture.md`](./architecture.md) para cómo se relacionan entre sí.

## Visión por computadora

| Tecnología | Uso |
|---|---|
| **Python** | Lenguaje principal del pipeline de visión. |
| **OpenCV** | Captura de cámara, corrección de perspectiva (homografía, `warpPerspective`), preprocesado de imagen. |
| **YOLOv8 / YOLOv11 (nano/small)** | Detección de cartas dentro del frame (localización, no identificación). |
| **ORB / SIFT** (feature matching) | Reconocimiento de qué carta es, comparando contra el dataset de referencia. |
| **Embeddings CNN** (a evaluar) | Alternativa/complemento a ORB para reconocimiento más robusto ante oclusión o ángulo. |
| **Tesseract OCR** | Lectura de contadores manuales (vida, DON) — no usado para identificar cartas. |

## Hardware

| Componente | Opciones |
|---|---|
| **Cámara** | USB (idealmente global shutter) o Raspberry Pi Camera Module, montaje cenital. |
| **Proyección** | Mini-proyector de corto alcance, o TV/monitor lateral como alternativa. |
| **Cómputo local** | Raspberry Pi 5 o mini-PC con GPU (Jetson Nano/Orin) para inferencia. |
| **Iluminación** | Anillo LED para normalizar contraste y reducir reflejos en fundas. |

## Backend / orquestación

| Tecnología | Uso |
|---|---|
| **FastAPI** | Servicio backend: recibe frames/resultados, mantiene el estado del juego, expone la API. |
| **WebSocket** | Publicación en tiempo real del estado del juego hacia el frontend. |
| **Docker** | Containerización del pipeline de visión y del backend. |
| **Kubernetes (k3s)** | Orquestación y despliegue en el homelab existente (Traefik, Flannel, local-path-provisioner). |
| **Prometheus / Grafana** | Observabilidad y métricas del sistema en producción. |

## Frontend / visualización

| Tecnología | Uso |
|---|---|
| **React** o **HTML + Canvas** | App web que consume el WebSocket y dibuja el overlay (vida, DON, keywords) sobre la mesa. |
| **Homografía cámara→proyector** | Calibración inicial (patrón de puntos) para que el overlay caiga sobre la carta correcta. |

## Dataset

| Formato | Uso |
|---|---|
| **Imágenes oficiales** (Bandai / TCGPlayer) | Set de referencia para el matching de reconocimiento. |
| **JSON** | Metadata de cada carta (nombre, coste, texto de habilidad, keywords). |

## Notas

- El stack prioriza modelos livianos (YOLO nano/small, ORB en vez de deep embeddings pesados) para sostener varios FPS en hardware modesto (RPi5 / Jetson).
- Todo el backend y el pipeline de visión están pensados para desplegarse en el **homelab k3s** ya existente, reutilizando la observabilidad (Prometheus/Grafana) ya montada.
