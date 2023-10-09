from typing import List
from fastapi import Depends, FastAPI, File, Header, Query, Response, UploadFile
import uvicorn
from Fooocus_api.api_utils import generation_output, narray_to_base64img, narray_to_bytesimg
from Fooocus_api.models import GeneratedImageBase64, GenerationFinishReason, ImgInpaintOrOutpaintRequest, ImgUpscaleOrVaryRequest, Text2ImgRequest
from Fooocus_api.task_queue import TaskQueue
from Fooocus_api.worker import process_generate

app = FastAPI()

task_queue = TaskQueue()

img_generate_responses = {
    "200": {
        "description": "PNG bytes if request's 'Accept' header is 'image/png', otherwise JSON",
        "content": {
            "application/json": {
                "example": [{
                    "base64": "...very long string...",
                    "seed": 1050625087,
                    "finish_reason": "SUCCESS"
                }]
            },
            "image/png": {
                "example": "PNG bytes, what did you expect?"
            }
        }
    }
}


@app.post("/v1/generation/text-to-image", response_model=List[GeneratedImageBase64], responses=img_generate_responses)
def text2img_generation(req: Text2ImgRequest, accept: str = Header(None),
                        accept_query: str | None = Query(None, alias='accept', description="Parameter to overvide 'Accept' header, 'image/png' for output bytes")):
    if accept_query is not None and len(accept_query) > 0:
        accept = accept_query

    if accept == 'image/png':
        streaming_output = True
        # image_number auto set to 1 in streaming mode
        req.image_number = 1
    else:
        streaming_output = False

    results = process_generate(req)
    return generation_output(results, streaming_output)


@app.post("/v1/generation/image-upscale-vary", response_model=List[GeneratedImageBase64], responses=img_generate_responses)
def img_upscale_or_vary(input_image: UploadFile, req: ImgUpscaleOrVaryRequest = Depends(ImgUpscaleOrVaryRequest.as_form),
                        accept: str = Header(None),
                        accept_query: str | None = Query(None, alias='accept', description="Parameter to overvide 'Accept' header, 'image/png' for output bytes")):
    if accept_query is not None and len(accept_query) > 0:
        accept = accept_query

    if accept == 'image/png':
        streaming_output = True
        # image_number auto set to 1 in streaming mode
        req.image_number = 1
    else:
        streaming_output = False

    results = process_generate(req)
    return generation_output(results, streaming_output)


@app.post("/v1/generation/image-inpait-outpaint", response_model=List[GeneratedImageBase64], responses=img_generate_responses)
def img_inpaint_or_outpaint(input_image: UploadFile, req: ImgInpaintOrOutpaintRequest = Depends(ImgInpaintOrOutpaintRequest.as_form),
                            accept: str = Header(None),
                            accept_query: str | None = Query(None, alias='accept', description="Parameter to overvide 'Accept' header, 'image/png' for output bytes")):
    if accept_query is not None and len(accept_query) > 0:
        accept = accept_query

    if accept == 'image/png':
        streaming_output = True
        # image_number auto set to 1 in streaming mode
        req.image_number = 1
    else:
        streaming_output = False

    results = process_generate(req)
    return generation_output(results, streaming_output)


def start_app(args):
    uvicorn.run("Fooocus_api.api:app", host=args.host,
                port=args.port, log_level=args.log_level)
