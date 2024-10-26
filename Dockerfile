FROM pytorch/pytorch

WORKDIR /app

COPY pyproject.toml .
COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY silero_api_server silero_api_server
RUN ls -la
RUN python3 --version

EXPOSE 8001

CMD python3 -m silero_api_server -o 0.0.0.0
