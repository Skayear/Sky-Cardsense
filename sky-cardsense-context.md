# sky-cardsense

Playmat viviente para TCG (One Piece Card Game): cámara cenital + visión por computadora para reconocer cartas en la mesa, y un proyector/TV que muestra referencias visuales y números en tiempo real sobre la partida.

## Concepto

- Cámara apuntando a la mesa desde arriba, leyendo qué cartas hay en juego.
- Proyector de corto alcance (o TV lateral como alternativa) mostrando overlays: vida, DON, contadores, referencias de keywords.
- Pensado primero para el mazo propio (Lucy Dressrosa Red/Blue, Blue Buggy), escalable a todo el card pool más adelante.

## Desafíos técnicos

1. **Detección y reconocimiento de cartas**: identificar qué carta es, no solo que hay una carta. OCR puro (Tesseract) da falsos positivos por el parecido entre cartas del mismo set — mejor resultado con matching de características visuales (ORB/SIFT o embeddings) contra una base de imágenes de referencia.
2. **Iluminación y ángulo de cámara**: sombras y reflejos en fundas rompen la detección. Requiere luz controlada (anillo LED) y normalización de contraste.
3. **Cartas superpuestas o tapadas**: diferenciar carta activa de pilas (mazo, cementerio) es un problema de segmentación no trivial.
4. **Latencia en tiempo real**: se necesita procesar varios FPS, no una foto cada tantos segundos — empuja a modelos livianos (YOLO nano/small) en vez de solo OCR.
5. **Registro espacial cámara↔proyector**: si el proyector pinta sobre la carta en la mesa, cámara y proyector deben calibrarse geométricamente entre sí (homografía cámara→proyector), no solo cámara→mesa.
6. **Base de datos de cartas actualizada**: el set crece con cada expansión (ya OP-16+); se necesita un pipeline de ingesta de nuevas cartas sin reescribir el sistema.
7. **UX de la interfaz visual**: decidir qué mostrar y cuándo sin saturar la mesa de información.

## Stack tecnológico

**Visión por computadora**
- Python + OpenCV: captura, corrección de perspectiva (homografía), preprocesado.
- Modelo de detección de objetos (YOLOv8/v11 nano/small) para localizar cartas en el frame.
- Reconocimiento de carta: feature matching (ORB) contra dataset propio, o embedding con CNN chica — más confiable que OCR puro para identificar cartas.
- Tesseract como complemento, solo para leer contadores manuales (vida, DON), no para identificar cartas.

**Hardware**
- Cámara USB o Raspberry Pi Camera Module, montada cenital (idealmente global shutter).
- Mini-proyector de corto alcance, o TV/monitor como alternativa para overlay lateral.
- Raspberry Pi 5 o mini-PC con GPU (Jetson Nano/Orin) para inferencia local.

**Backend / orquestación**
- FastAPI: recibe frames, corre detección, publica estado del juego.
- WebSocket para estado del juego en tiempo real hacia el frontend.
- Containerizado (Docker), desplegable en el cluster k3s del homelab existente.
- Observabilidad con Prometheus/Grafana (ya montado en el homelab).

**Frontend / visualización**
- App web (React o HTML+Canvas) consumiendo el WebSocket y dibujando overlays.
- Calibración inicial cámara→proyector (patrón de puntos, ajuste de homografía).

**Dataset de cartas**
- Imágenes oficiales de Bandai/TCGPlayer + texto de habilidades, en JSON.
- Empezar con dataset chico (mazo propio: Lucy, Blue Buggy) antes de escalar a todo el pool.

## Plan por fases (issues)

### Fase 1 — Setup
- Definir arquitectura general del sistema (diagrama de componentes y flujo de datos)
- Estructurar el repositorio (carpetas vision/, backend/, frontend/, dataset/, docs/; README; licencia; .gitignore)
- Seleccionar y adquirir hardware (cámara, proyector/TV, mini-PC/Jetson/RPi5)
- Montaje físico de cámara cenital (soporte estable a altura fija)

### Fase 2 — Visión por computadora (MVP)
- Prototipo de captura de cámara con OpenCV (validar FPS/resolución mínima)
- Corrección de perspectiva de la mesa (homografía, warpPerspective)
- Detección de contornos de cartas (rectángulos candidatos por ratio de aspecto)
- Armar dataset inicial con mazo propio (Lucy Dressrosa Red/Blue, Blue Buggy)
- Reconocimiento de carta por feature matching (ORB/SIFT)
- Evaluar OCR (Tesseract) como complemento para contadores manuales
- Manejo de iluminación (anillo LED, normalización de contraste)

### Fase 3 — Backend
- Servicio backend (FastAPI) para estado del juego
- WebSocket para publicar estado en tiempo real
- Modelo de datos de cartas y pipeline de ingesta de nuevas expansiones
- Containerizar el pipeline de visión (Dockerfile)
- Desplegar en el cluster k3s del homelab, métricas en Prometheus/Grafana

### Fase 4 — Frontend / Proyección
- App web de overlay (React/Canvas) consumiendo el WebSocket
- Diseño UX de la interfaz en mesa (qué mostrar y cuándo)
- Calibración cámara-proyector (homografía proyector)
- Modo alternativo con TV/monitor lateral (sin proyección directa)

### Fase 5 — Robustez y escalado
- Manejo de cartas superpuestas o parcialmente tapadas
- Optimizar latencia de inferencia (modelo liviano / GPU)
- Expandir dataset a todo el card pool (todas las expansiones)
- Documentación y guía de instalación (montaje, software, calibración)

## Notas de contexto del autor

- SRE/DevOps, cómodo con AWS, Kubernetes/EKS, Terraform, GitHub Actions, Grafana/Prometheus.
- Tiene homelab Kubernetes (k3s single-node, Traefik/Flannel/local-path-provisioner) con Prometheus/Grafana ya configurados — reutilizable para desplegar este proyecto.
- Interés previo en proyectos con Raspberry Pi (incluyendo IA/asistentes con Whisper, Ollama, Home Assistant).
- Juega One Piece TCG competitivamente; mazos de referencia: Lucy (Dressrosa Red/Blue), Blue Buggy (Cross Guild), Vinsmoke/Germa 66.
