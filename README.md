# Sky-Cardsense

Playmat viviente para **One Piece Card Game**: una cámara cenital con visión por computadora reconoce las cartas sobre la mesa, y un proyector (o TV lateral) muestra en tiempo real overlays con vida, DON, contadores y referencias de keywords.

> 🚧 Proyecto en fase de diseño/planificación. Ver el detalle completo en [`sky-cardsense-context.md`](./sky-cardsense-context.md) y el seguimiento por fases en los [Issues](../../issues).

## Concepto

- Cámara apuntando a la mesa desde arriba, leyendo qué cartas hay en juego.
- Proyector de corto alcance (o TV lateral como alternativa) mostrando overlays: vida, DON, contadores, referencias de keywords.
- Pensado primero para el mazo propio (Lucy Dressrosa Red/Blue, Blue Buggy), escalable a todo el card pool más adelante.

## Desafíos técnicos

- **Reconocimiento de cartas**: identificar qué carta es exactamente, no solo detectar que hay una carta — feature matching (ORB/SIFT) o embeddings en vez de OCR puro.
- **Iluminación y ángulo de cámara**: sombras y reflejos en fundas rompen la detección.
- **Cartas superpuestas o tapadas**: diferenciar carta activa de pilas (mazo, cementerio).
- **Latencia en tiempo real**: procesar varios FPS con modelos livianos (YOLO nano/small).
- **Registro espacial cámara↔proyector**: calibración geométrica (homografía) entre cámara y proyector.
- **Base de datos de cartas actualizada**: pipeline de ingesta para nuevas expansiones (ya OP-16+).
- **UX de la interfaz visual**: qué mostrar y cuándo, sin saturar la mesa de información.

## Stack tecnológico

**Visión por computadora**
- Python + OpenCV (captura, corrección de perspectiva, preprocesado)
- YOLOv8/v11 nano/small para detección de cartas en el frame
- Feature matching (ORB) o embeddings CNN para reconocimiento de carta
- Tesseract como complemento para contadores manuales (vida, DON)

**Hardware**
- Cámara USB o Raspberry Pi Camera Module, montaje cenital (idealmente global shutter)
- Mini-proyector de corto alcance, o TV/monitor como alternativa
- Raspberry Pi 5 o mini-PC con GPU (Jetson Nano/Orin) para inferencia local

**Backend / orquestación**
- FastAPI + WebSocket para publicar el estado del juego en tiempo real
- Containerizado (Docker), desplegable en el cluster k3s del homelab
- Observabilidad con Prometheus/Grafana

**Frontend / visualización**
- App web (React o HTML+Canvas) consumiendo el WebSocket y dibujando overlays
- Calibración cámara→proyector (patrón de puntos, ajuste de homografía)

**Dataset de cartas**
- Imágenes oficiales de Bandai/TCGPlayer + texto de habilidades, en JSON
- Empieza con dataset chico (mazo propio) antes de escalar a todo el pool

## Roadmap por fases

| Fase | Descripción | Issue |
|------|-------------|-------|
| 1 | Setup (arquitectura, estructura de repo, hardware, montaje) | [#1](../../issues/1) |
| 2 | Visión por computadora (MVP) | [#2](../../issues/2) |
| 3 | Backend | [#3](../../issues/3) |
| 4 | Frontend / Proyección | [#4](../../issues/4) |
| 5 | Robustez y escalado | [#5](../../issues/5) |

## Notas de contexto

- Perfil del autor: SRE/DevOps, cómodo con AWS, Kubernetes/EKS, Terraform, GitHub Actions, Grafana/Prometheus.
- Homelab Kubernetes propio (k3s single-node, Traefik/Flannel/local-path-provisioner) con Prometheus/Grafana ya configurados, reutilizable para este proyecto.
- Mazos de referencia: Lucy (Dressrosa Red/Blue), Blue Buggy (Cross Guild), Vinsmoke/Germa 66.
