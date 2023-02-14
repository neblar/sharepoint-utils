FROM selenium/standalone-chrome-debug:latest

USER root

RUN apt-get update && apt-get install -y python3-pip

RUN pip install selenium tqdm httpx

WORKDIR /home/workspace

ENTRYPOINT [ "python3", "-m", "sharepoint_utils" ]