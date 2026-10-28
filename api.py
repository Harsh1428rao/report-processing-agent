
import base64
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, Body

from process_report import process_report


app = FastAPI(
    title="Report Processing Agent",
    description="Upload a CSV to profile, validate, and clean it.",
    version="1.2.0",
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# def process_saved_csv(input_path: Path, original_name: str):
#     try:
#         report = process_report(str(input_path))

#         return {
#             "original_filename": original_name,
#             "processing_status": report["processing_status"],
#             "review_required": report["review_required"],
#             "profile": report["profile"],
#             "validation": report["validation"],
#             "cleaning": report["cleaning"],
#             "report_file": report["report_file"],
#         }

#     except (ValueError, OSError) as error:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Could not process the CSV: {error}",
#         ) from error

def process_saved_csv(input_path: Path, original_name: str):
    try:
        report = process_report(str(input_path))

        cleaned_filename = report["cleaning"]["output_file"]
        cleaned_path = input_path.parent / cleaned_filename

        if not cleaned_path.exists():
            raise HTTPException(
                status_code=500,
                detail="The cleaned CSV file was not created.",
            )

        cleaned_csv_base64 = base64.b64encode(
            cleaned_path.read_bytes()
        ).decode("ascii")

        return {
            "original_filename": original_name,
            "processing_status": report["processing_status"],
            "review_required": report["review_required"],
            "profile": report["profile"],
            "validation": report["validation"],
            "cleaning": report["cleaning"],
            "report_file": report["report_file"],
            "cleaned_filename": cleaned_filename,
            "cleaned_csv_base64": cleaned_csv_base64,
        }

    except HTTPException:
        raise

    except (ValueError, OSError) as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not process the CSV: {error}",
        ) from error


@app.get("/")
def home():
    return {
        "message": "Report Processing Agent is running",
        "status": "ready",
    }


@app.post("/process")
def process_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    original_name = Path(file.filename).name
    input_path = OUTPUT_DIR / original_name

    try:
        with input_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        return process_saved_csv(input_path, original_name)

    except OSError as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not save the CSV: {error}",
        ) from error

    finally:
        file.file.close()


@app.post("/process-raw")
def process_raw_csv(
    payload: dict = Body(...),
    filename: str = "upload.csv",
):
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="The filename must end in .csv.",
        )

    encoded_content = payload.get("content_base64")

    if not isinstance(encoded_content, str) or not encoded_content:
        raise HTTPException(
            status_code=400,
            detail="Missing Base64 CSV content.",
        )

    try:
        content = base64.b64decode(
            encoded_content,
            validate=True,
        )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV content is empty.",
            )

        original_name = Path(filename).name
        input_path = OUTPUT_DIR / original_name
        input_path.write_bytes(content)

        return process_saved_csv(input_path, original_name)

    except (ValueError, OSError) as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not process the CSV: {error}",
        ) from error
