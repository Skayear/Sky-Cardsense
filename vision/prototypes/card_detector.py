"""
Prototipo de captura + detección de cartas (Fase 2).

Abre la webcam, busca contornos rectangulares con el ratio de aspecto de una
carta de TCG estándar (63x88mm) y muestra el recorte rectificado (warp) de la
primera carta detectada. Sirve como base para luego sumar reconocimiento por
feature matching (ORB) contra un dataset de referencia.

Detecta candidatos por dos vías en paralelo:
  1. Bordes (Canny + contraste) — funciona bien con cartas de borde/marco definido.
  2. Color de fondo — segmenta la mesa por color (HSV) e identifica todo lo
     que no es mesa como candidato. No depende del arte de la carta, así que
     funciona también con cartas full art / foil donde el borde no siempre
     es detectable por contraste.

Controles:
  q - salir
  s - guardar el recorte rectificado actual en dataset/raw/ (para ir armando
      el dataset de referencia)
  b - calibrar el color de fondo: apuntá la cámara a la mesa VACÍA (sin
      cartas) y presioná 'b'. Se guarda en table_calibration.json.

Uso:
  python card_detector.py [--camera 0] [--width 1280] [--height 720]
"""

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

CARD_ASPECT_RATIO = 63 / 88  # ancho/alto de una carta estándar (63x88mm)
ASPECT_TOLERANCE = 0.15
MIN_AREA_RATIO = 0.01  # % mínimo del área del frame para considerar un candidato
MAX_AREA_RATIO = 0.60
WARP_SIZE = (300, 420)  # tamaño del recorte rectificado (mantiene el ratio 63:88)

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset" / "raw"
CALIB_PATH = Path(__file__).resolve().parent / "table_calibration.json"


def order_points(pts: np.ndarray) -> np.ndarray:
    """Ordena 4 puntos como top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


MIN_EXTENT = 0.80  # cuánto debe llenar el contorno su rectángulo mínimo rotado
CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


def auto_canny(image: np.ndarray, sigma: float = 0.33) -> np.ndarray:
    """Umbrales de Canny adaptados al brillo de la imagen (mediana), en vez de
    valores fijos que fallan si cambia la luz."""
    v = float(np.median(image))
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    return cv2.Canny(image, lower, upper)


def preprocess(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = CLAHE.apply(gray)  # normaliza contraste (sombras/reflejos en fundas)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = auto_canny(blurred)
    # cierra bordes rotos (por reflejos o esquinas redondeadas de la carta)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
    return edges


def find_card_candidates(frame: np.ndarray, mask: np.ndarray) -> list[np.ndarray]:
    """Busca rectángulos tipo-carta en una máscara binaria. Sirve tanto para
    un mapa de bordes (Canny) como para una máscara de primer plano (fondo
    segmentado por color) — en ambos casos son contornos cerrados."""
    frame_area = frame.shape[0] * frame.shape[1]

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        area_ratio = area / frame_area
        if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
            continue

        rect = cv2.minAreaRect(cnt)
        (w, h) = rect[1]
        if w == 0 or h == 0:
            continue

        # en vez de exigir un polígono de exactamente 4 vértices (falla con
        # esquinas redondeadas o ruido en el borde), medimos qué tan
        # rectangular es el contorno comparándolo con su rectángulo mínimo
        rect_area = w * h
        extent = area / rect_area
        if extent < MIN_EXTENT:
            continue

        ratio = min(w, h) / max(w, h)
        if abs(ratio - CARD_ASPECT_RATIO) > ASPECT_TOLERANCE:
            continue

        box = cv2.boxPoints(rect).astype("float32")
        candidates.append(box)

    return candidates


def merge_candidates(candidates: list[np.ndarray], dist_thresh: float = 40) -> list[np.ndarray]:
    """Descarta duplicados cuando bordes y color detectan la misma carta."""
    merged: list[np.ndarray] = []
    for cand in candidates:
        center = cand.mean(axis=0)
        if any(np.linalg.norm(center - m.mean(axis=0)) < dist_thresh for m in merged):
            continue
        merged.append(cand)
    return merged


def sample_background_hsv(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Toma el color de la mesa vacía (centro del frame, para evitar bordes/
    viñeteado) y arma un rango HSV tolerante a variaciones de luz."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, w = hsv.shape[:2]
    mh, mw = int(h * 0.15), int(w * 0.15)
    sample = hsv[mh : h - mh, mw : w - mw].reshape(-1, 3).astype(np.float32)

    lower = np.percentile(sample, 2, axis=0)
    upper = np.percentile(sample, 98, axis=0)

    margin = np.array([10, 40, 40])
    lower = lower - margin
    upper = upper + margin
    lower[0], upper[0] = np.clip([lower[0], upper[0]], 0, 179)
    lower[1:], upper[1:] = np.clip(lower[1:], 0, 255), np.clip(upper[1:], 0, 255)

    return lower.astype(np.uint8), upper.astype(np.uint8)


def compute_background_mask(frame: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    background = cv2.inRange(hsv, lower, upper)
    foreground = cv2.bitwise_not(background)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), iterations=2)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    return foreground


def load_calibration() -> tuple[np.ndarray, np.ndarray] | None:
    if not CALIB_PATH.exists():
        return None
    data = json.loads(CALIB_PATH.read_text())
    return np.array(data["lower"], dtype=np.uint8), np.array(data["upper"], dtype=np.uint8)


def save_calibration(lower: np.ndarray, upper: np.ndarray) -> None:
    CALIB_PATH.write_text(json.dumps({"lower": lower.tolist(), "upper": upper.tolist()}))


def warp_card(frame: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = order_points(pts)
    dst = np.array(
        [[0, 0], [WARP_SIZE[0] - 1, 0], [WARP_SIZE[0] - 1, WARP_SIZE[1] - 1], [0, WARP_SIZE[1] - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(frame, matrix, WARP_SIZE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la cámara {args.camera}")

    prev_time = time.time()
    last_warp = None
    calibration = load_calibration()
    if calibration:
        print("Calibración de fondo cargada desde table_calibration.json")

    print("Presioná 'q' para salir, 's' para guardar el recorte, 'b' para calibrar el fondo (mesa vacía).")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("No se pudo leer frame de la cámara.")
                break

            edges = preprocess(frame)
            candidates = find_card_candidates(frame, edges)

            cv2.imshow("Debug: bordes", edges)

            if calibration:
                bg_mask = compute_background_mask(frame, *calibration)
                candidates = merge_candidates(candidates + find_card_candidates(frame, bg_mask))
                cv2.imshow("Debug: fondo (mesa)", bg_mask)

            for pts in candidates:
                cv2.polylines(frame, [pts.astype(int)], True, (0, 255, 0), 2)

            if candidates:
                last_warp = warp_card(frame, candidates[0])
                cv2.imshow("Carta detectada (rectificada)", last_warp)

            now = time.time()
            fps = 1 / (now - prev_time) if now != prev_time else 0
            prev_time = now
            cv2.putText(
                frame,
                f"FPS: {fps:.1f}  candidatos: {len(candidates)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )

            cv2.imshow("Sky-Cardsense - card_detector", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s") and last_warp is not None:
                out_path = DATASET_DIR / f"captura_{int(time.time())}.png"
                cv2.imwrite(str(out_path), last_warp)
                print(f"Guardado: {out_path}")
            elif key == ord("b"):
                lower, upper = sample_background_hsv(frame)
                calibration = (lower, upper)
                save_calibration(lower, upper)
                print(f"Fondo calibrado: H[{lower[0]}-{upper[0]}] S[{lower[1]}-{upper[1]}] V[{lower[2]}-{upper[2]}]")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        cv2.waitKey(1)  # procesa el evento de cierre antes de que termine el proceso


if __name__ == "__main__":
    main()
