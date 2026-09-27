"""Smoke test manual del Analista contra FastAPI y un Ollama real.

Ejecutar desde la raíz: ``python backend/scripts/test_analyst_local.py``.
No forma parte de pytest ni descarga modelos.
"""

import argparse
import json
import sys

import httpx


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Prueba manual del Analista IA local")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--question", default="¿Cuál es la variante más frecuente?")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ejecuta las seis preguntas de demostración y resume tools y tiempos.",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    # La primera carga en CPU puede superar el timeout predeterminado de 60 s.
    with httpx.Client(timeout=240) as client:
        status = client.get(f"{base_url}/api/v1/analyst/status")
        status.raise_for_status()
        status_data = status.json()
        print(json.dumps(status_data, ensure_ascii=False, indent=2), flush=True)
        if not status_data.get("available"):
            raise SystemExit("Ollama o el modelo configurado no están disponibles.")

        questions = (
            [
                "¿Cuál es la variante más frecuente?",
                "¿Qué transición tiene mayor duración?",
                "¿Cuántos casos tienen retrabajo?",
                "¿Qué desviaciones tiene DEMO-00089?",
                "¿Por qué DEMO-00141 tiene riesgo alto?",
                "¿Cuál es el estado de la alerta de DEMO-00141?",
            ]
            if args.all
            else [args.question]
        )
        for question in questions:
            response = client.post(
                f"{base_url}/api/v1/analyst/chat",
                json={"message": question, "history": [], "context_case_code": None},
            )
            response.raise_for_status()
            result = response.json()
            if args.all:
                print(json.dumps({
                    "question": question,
                    "answer": result["answer"],
                    "tool_calls": result["tool_calls"],
                    "evidence": result["evidence"],
                    "duration_ms": result["duration_ms"],
                    "tool_rounds": result["tool_rounds"],
                }, ensure_ascii=False), flush=True)
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
