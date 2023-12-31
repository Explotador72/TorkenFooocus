import argparse
import os
import re
import shutil
import subprocess
import sys
from importlib.util import find_spec

from fooocus_api_version import version
from fooocusapi.repositories_versions import fooocus_commit_hash

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

python = sys.executable
default_command_live = True
index_url = os.environ.get('INDEX_URL', "")
re_requirement = re.compile(r"\s*([-_a-zA-Z0-9]+)\s*(?:==\s*([-+_.a-zA-Z0-9]+))?\s*")

fooocus_name = 'Fooocus'

modules_path = os.path.dirname(os.path.realpath(__file__))
script_path = modules_path
dir_repos = "repositories"


def download_repositories():
    import pygit2

    pygit2.option(pygit2.GIT_OPT_SET_OWNER_VALIDATION, 0)

    http_proxy = os.environ.get('HTTP_PROXY')
    https_proxy = os.environ.get('HTTPS_PROXY')
    
    if http_proxy != None:
        print(f"Using http proxy for git clone: {http_proxy}")
        os.environ['http_proxy'] = http_proxy

    if https_proxy != None:
        print(f"Using https proxy for git clone: {https_proxy}")
        os.environ['https_proxy'] = https_proxy

    # Check and download Fooocus
    fooocus_repo = os.environ.get(
        'FOOOCUS_REPO', 'https://github.com/lllyasviel/Fooocus')
    git_clone(fooocus_repo, repo_dir(fooocus_name),
              "Fooocus", fooocus_commit_hash)
    

def is_installed(package):
    try:
        spec = find_spec(package)
    except ModuleNotFoundError:
        return False

    return spec is not None


def download_models():
    vae_approx_filenames = [
        ('xlvaeapp.pth', 'https://huggingface.co/lllyasviel/misc/resolve/main/xlvaeapp.pth'),
        ('vaeapp_sd15.pth', 'https://huggingface.co/lllyasviel/misc/resolve/main/vaeapp_sd15.pt'),
        ('xl-to-v1_interposer-v3.1.safetensors',
        'https://huggingface.co/lllyasviel/misc/resolve/main/xl-to-v1_interposer-v3.1.safetensors')
    ]

    from modules.model_loader import load_file_from_url
    from modules.path import modelfile_path, lorafile_path, vae_approx_path, fooocus_expansion_path, \
        checkpoint_downloads, embeddings_path, embeddings_downloads, lora_downloads

    for file_name, url in checkpoint_downloads.items():
        load_file_from_url(url=url, model_dir=modelfile_path, file_name=file_name)
    for file_name, url in embeddings_downloads.items():
        load_file_from_url(url=url, model_dir=embeddings_path, file_name=file_name)
    for file_name, url in lora_downloads.items():
        load_file_from_url(url=url, model_dir=lorafile_path, file_name=file_name)
    for file_name, url in vae_approx_filenames:
        load_file_from_url(url=url, model_dir=vae_approx_path, file_name=file_name)

    load_file_from_url(
        url='https://huggingface.co/lllyasviel/misc/resolve/main/fooocus_expansion.bin',
        model_dir=fooocus_expansion_path,
        file_name='pytorch_model.bin'
    )


def prepare_environments(args) -> bool:
    torch_index_url = os.environ.get('TORCH_INDEX_URL', "https://download.pytorch.org/whl/cu121")

    # Check if need pip install
    requirements_file = 'requirements.txt'
    if not requirements_met(requirements_file):
        run_pip(f"install -r \"{requirements_file}\"", "requirements")

    if not is_installed("torch") or not is_installed("torchvision"):
        print(f"torch_index_url: {torch_index_url}")
        run_pip(f"install torch==2.0.1 torchvision==0.15.2 --extra-index-url {torch_index_url}", "torch")

    if not is_installed('xformers'):
        run_pip("install xformers==0.0.21", "xformers")

    skip_sync_repo = False
    if args.sync_repo is not None:
        if args.sync_repo == 'only':
            print("Only download and sync depent repositories")
            download_repositories()
            models_path = os.path.join(
                script_path, dir_repos, fooocus_name, "models")
            print(
                f"Sync repositories successful. Now you can put model files in subdirectories of '{models_path}'")
            return False
        elif args.sync_repo == 'skip':
            skip_sync_repo = True
        else:
            print(
                f"Invalid value for argument '--sync-repo', acceptable value are 'skip' and 'only'")
            exit(1)

    if not skip_sync_repo:
        download_repositories()

    # Add dependent repositories to import path
    sys.path.append(script_path)
    fooocus_path = os.path.join(script_path, dir_repos, fooocus_name)
    sys.path.append(fooocus_path)
    backend_path = os.path.join(fooocus_path, 'backend', 'headless')
    if backend_path not in sys.path:
        sys.path.append(backend_path)
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    sys.argv = [sys.argv[0]]
    download_models()
    ini_cbh_args()

    if args.preload_pipeline:
        print("Preload pipeline")
        import modules.default_pipeline as _

    return True

def pre_setup(skip_sync_repo: bool=False, disable_private_log: bool=False, load_all_models: bool=False, preload_pipeline: bool=False):
    class Args(object):
        sync_repo = None
        preload_pipeline = False

    print("[Pre Setup] Prepare environments")

    args = Args()
    args.preload_pipeline = preload_pipeline
    if skip_sync_repo:
        args.sync_repo = 'skip'
    prepare_environments(args)

    if disable_private_log:
        import fooocusapi.worker as worker
        worker.save_log = False

    if load_all_models:
        import modules.path as path
        from fooocusapi.parameters import inpaint_model_version
        path.downloading_upscale_model()
        path.downloading_inpaint_models(inpaint_model_version)
        path.downloading_controlnet_canny()
        path.downloading_controlnet_cpds()
        path.downloading_ip_adapters()
    print("[Pre Setup] Finished")


# This function was copied from [Fooocus](https://github.com/lllyasviel/Fooocus) repository.
def ini_cbh_args():
    from args_manager import args
    return args


if __name__ == "__main__":
    print(f"Python {sys.version}")
    print(f"Fooocus-API version: {version}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8888,
                        help="Set the listen port")
    print('done1')
    parser.add_argument("--host", type=str,
                        default='127.0.0.1', help="Set the listen host")
    print('done2')
    parser.add_argument("--log-level", type=str,
                        default='info', help="Log info for Uvicorn")
    print('done3')
    parser.add_argument("--sync-repo", default=None,
                        help="Sync dependent git repositories to local, 'skip' for skip sync action, 'only' for only do the sync action and not launch app")
    print('done4')
    parser.add_argument("--preload-pipeline", default=False, action="store_true", help="True for preload pipeline before start http server")

    args = parser.parse_args()

    if prepare_environments(args):
        sys.argv = [sys.argv[0]]

        # Start api server
        from fooocusapi.api import start_app
        start_app(args)
