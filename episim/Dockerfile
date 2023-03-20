FROM python:3.9.1 AS builder
COPY requirements.txt .

RUN pip install --user -r requirements.txt

FROM python:3.9.1-slim
WORKDIR /code

COPY --from=builder /root/.local /root/.local
COPY ./src .

ENV PATH=/root/.local:$PATH

CMD [ "python", "-u", "./main.py" ]
