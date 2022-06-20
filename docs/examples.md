# Build-magic Examples

Below, you will find a collection of example build-magic use cases. If you want to run any of the examples yourself, clone the [build-magic-examples](https://github.com/cmmorrow/build-magic-examples) repository to get started.

* [Distributing A Python Package](examples.md#distributing-a-python-package)
* [Converting An OpenAPI Schema To Slate With Widdershins](examples.md#converting-an-openapi-schema-to-slate-with-widdershins)
* [Building And Testing A Docker Image In a Virtual Machine](examples.md#building-and-testing-a-docker-image-in-a-virtual-machine)
* [Automating A Machine Learning Pipeline](examples.md#automating-a-machine-learning-pipeline)

## Distributing A Python Package

Test, build, and release a Python package to the [python package index](https://pypi.org/).

This Config File assumes you have a Python package with a setup.py file, a pypi.org account, pypi.org credentials available in $PATH, documentation on GitHub pages, and the pytest, flake8, mkdocs, and twine packages installed.

To run the Config File, execute `build-magic -C release.yaml`.

### Code

=== "release.yaml"

```yaml
build-magic:
  - stage:
      name: Run Tests
      commands:
        - execute: flake8 --count --show-source --statistics
        - test: pytest -c unit_test.toml
  - stage:
      name: Build Documentation
      action: cleanup
      commands:
        - build: mkdocs build
        - deploy: mkdocs gh-deploy
  - stage:
      name: Deploy to PyPI
      action: cleanup
      commands:
        - build: python setup.py sdist bdist_wheel --universal
        - release: twine upload dist/*
```

## Converting An OpenAPI Schema To Slate With Widdershins

Builds API documentation for an OpenAPI schema.

This example assumes you have Docker installed.

### Explanation

The build process for the documentation is split into five stages:

* prep
* fetch
* convert
* build
* cleanup

To ensure the build pipeline runs on any machine, each stage is run in a Docker container. The prep stage builds the images that will be used by the fetch, convert, and build stages.

The fetch stage downloads the petstore OpenAPI schema that will be used by this example and pretty prints it to the file petstore3.json with jq.

The convert step uses the widdershins npm package convert the petstore3.json file to markdown that can be consumed by slate.

The build stage uses the slate Ruby package to generate the documentation. Slate uses middleman to build the docs is picky about filesystem structure, so the working directory needs to be set as the directory with Slate's boilerplate code. The name of the markdown file also needs to be changed to index.html.md. The build docs are then extracted and exposed to the file system on the host machine through the bind directory /app.

Finally, the cleanup step remove the Docker images created for each stage so as to not take up extra disk space and provide clean images each time.

Notice how most of the heavy lifting is shifted to the Dockerfiles associated with each step. This encapsulates the setup and applications needed for each stage in the Dockerfile, and the build_docs.yaml Config File only contains the commands needed for building the docs. This also has the advantage that if wget, jq, widdershins, and slate are installed on the host machine, the Config File can be easily modified to use the local command runner without having to modify the executed commands.

To run the Config File, execute `build-magic -C build_docs.yaml`.

### Code

=== "build_docs.yaml"

```yaml
build-magic:
  - stage:
      name: prep
      commands:
        - build: docker build -t fetch ./fetch
        - build: docker build -t widdershins ./widdershins
        - build: docker build -t slate ./slate
  - stage:
      name: fetch
      runner: docker
      environment: fetch
      commands: 
        - execute: wget https://petstore3.swagger.io/api/v3/openapi.json
        - execute: cat openapi.json | jq > petstore3.json
        - execute: rm openapi.json
  - stage:
      name: convert
      runner: docker
      environment: widdershins
      commands:
        - execute: widdershins --summary petstore3.json petstore3.md
  - stage:
      name: build
      runner: docker
      environment: slate
      working directory: /srv/slate/source
      parameters:
        bind: /app
      commands:
        - execute: cp /app/petstore3.md /srv/slate/source/index.html.md
        - build: bundle exec middleman build
        - execute: cp -r /srv/slate/build /app
  - stage:
      name: cleanup
      commands:
        - execute: docker rmi fetch
        - execute: docker rmi widdershins
        - execute: docker rmi slate
```

=== "fetch/Dockerfile"

    ```dockerfile
    FROM alpine:latest
    RUN apk add wget jq
    CMD [ "/bin/sh" ]
    ```

=== "widdershins/Dockerfile"

    ```dockerfile
    FROM node:alpine
    RUN npm install -g widdershins
    CMD [ "/bin/sh" ]
    ```

=== "slate/Dockerfile"

    ```dockerfile
    FROM ruby:slim
    RUN apt update && \
    apt install -y build-essential nodejs tar wget
    RUN wget https://github.com/slatedocs/slate/archive/refs/tags/v2.12.0.tar.gz && \
    tar -xzf v2.12.0.tar.gz && \
    mv slate-2.12.0 /srv/slate
    RUN gem install bundler && \
    BUNDLE_GEMFILE="/srv/slate/Gemfile" bundle install
    CMD [ "/bin/sh" ]
    ```

## Building And Testing A Docker Image In a Virtual Machine

Builds a Docker image in a virtual machine.

This example assumes you have Vagrant installed.

### Explanation

This example uses the Vagrant runner and the Alpine Linux Vagrant Box, as defined in the Vagrantfile. The docker and curl packages are installed and Docker is started. Next, the Docker image is built from the Dockerfile.

The Dockerfile is available in the virtual machine by setting the working directory and bind directory to **/app**. By doing this, the Vagrantfile is updated on the fly to include `config.vm.synced_folder ".", "/app"` which syncs the current directory on the host machine with the /app directory in the virtual machine.

Next, the Docker image is run and curl is used to call the web service running the Docker container. If the response from the container is what's expected by the test, it passes and we know the image for our web service was built correctly. The image is then tagged and pushed to an image repository on AWS.

To run the Config File, execute `build-magic -C build_image.yaml -v app myapp -v port 3000`.

### Code

=== "build_image.yaml"

```yaml
build-magic:
  - stage:
      name: Docker build example
      runner: vagrant
      environment: Vagrantfile
      working directory: /app
      parameters:
        bind: /app
      commands:
        - install: sudo apk update && sudo apk add docker curl
          label: Install docker and curl
        - execute: sudo service docker start
          label: Start dockerd
        - build: sudo docker build -t {{ app }} .
          label: Build docker image
        - execute: sudo docker run -d --rm --name {{ app }} -p {{ port }}:3000 {{ app }}
          label: Run the docker container
        - execute: sleep 5
          label: Wait 5 seconds for the container to start
        - test: export RESULT=`curl -s http://localhost:{{ port }}` && test "$RESULT" = '{"message":"Hello World"}'
          label: Test the endpoint
        - execute: sudo docker stop {{ app }}
          label: Stop the docker container
        - execute: sudo docker tag {{ app }}:latest {{ account_id }}.dkr.ecr.us-east-1.amazonaws.com/{{ app }}:latest
        - release: sudo docker push {{ account_id }}.dkr.ecr.us-east-1.amazonaws.com/{{ app }}:latest
```

=== "Vagrantfile"

```ruby
Vagrant.configure("2") do |config|
    config.vm.box = "generic/alpine312"
end
```

=== "Dockerfile"

```dockerfile
FROM alpine:latest
WORKDIR /app
COPY main.py requirements.txt /app/
RUN apk add python3 py3-pip
RUN pip3 install -r requirements.txt
EXPOSE 3000
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
```

=== "main.py"

```python
from fastapi import FastAPI


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
```

## Automating A Machine Learning Pipeline

A data pipeline that loads data, trains a model, and deploys the model to a web service.

This example assumes you have Docker installed. A virtual environment should also be used to install python 3.6+ and the dependencies in requirements.txt.

Before running the pipeline, the webserver that uses the model should be started by running the start_server.sh script.

### Explanation

The pipeline is split into three stages:

* etl
* train
* deploy

The etl stage starts by downloading the winequality-red dataset as a csv file. It then runs **etl.py** which abstracts away the details of converting the csv file to a feather file.

The train stage abstracts away details about training a model based on the data in the feather file. This allows for flexibility in defining a model by providing a single interface (**train.py**) that can accept input arguments from the command-line for building the model. The output of **train.py** is written to a text file and the model, as a pickle file, is gpg signed and encrypted for improved security. This step is likely unnecessary when running the webserver on the same machine where the model is generated, but is recommend when uploading the model to a different machine.

The deploy stage will remove the model currently being used by the webserver, and gpg decrypt and verify the new model. The webserver is then restarted and will pick up and use the new model.

Before running the Config File, the web server should be started with `docker run -d -p 3000:3000 -v $PWD/data/deploy:/app/data/deploy:ro --name model_server model_server`.

To run the Config File, execute ```
build-magic -C pipeline.yaml -v filename winequality-red_`date "+%Y%m%d%H%M%S"` -v user xxxxx -v server model_server```.

### Code

=== "pipeline.yaml"

```yaml
build-magic:
  - stage:
      name: etl
      commands:
        - execute: curl "http://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv" --output {{ filename }}.csv
          label: Download the dataset
        - execute: python3 etl.py {{ filename }}.csv
          label: Convert the dataset to Arrow
        - execute: mv {{ filename }}.feather data/input
        - execute: rm {{ filename }}.csv
  - stage:
      name: train
      commands:
        - execute: python3 train.py data/input/{{ filename }}.feather 0.1 0.1 > data/stats/{{ filename }}.stats
          label: Train the model
        - execute: mv {{ filename }}.pickle data/models/{{ filename }}.pickle
        - execute: gpg --output data/models/{{ filename }}.sig -se -r {{ user }} data/models/{{ filename }}.pickle
          label: Sign and encrypt the model
  - stage:
      name: deploy
      commands:
        - execute: rm -f data/deploy/*
        - execute: cp data/models/{{ filename }}.sig data/deploy
        - execute: gpg --output data/deploy/{{ filename }}.pickle -d data/deploy/{{ filename }}.sig
          label: Verify and decrypt the model
        - execute: rm data/deploy/{{ filename }}.sig
        - execute: docker restart {{ server }}
          label: Restart the web server
```

#### The Server

The webserver has a single endpoint, **/predict**, which accepts a JSON payload. Each key in the JSON payload corresponds to a field in the winequality-red dataset.

=== "server.py"

```python
import os
from pathlib import Path
import pickle

from fastapi import FastAPI
import pandas as pd
from pydantic import BaseModel


MODEL_PATH = os.environ.get('MODEL_PATH', '.')

app = FastAPI()

loaded = False
_model = None

class Vector(BaseModel):
    fixed_acidity: float
    volatile_acidity: float
    citric_acid: float
    residual_sugar: float
    chlorides: float
    free_sulfur_dioxide: float
    total_sulfur_dioxide: float
    density: float
    ph: float
    sulphates: float
    alcohol: float

    def convert(self):
        return pd.DataFrame(
            self.dict().values(),
            index=pd.Index(
                [
                    'fixed acidity',
                    'volatile acidity',
                    'citric acid',
                    'residual sugar',
                    'chlorides',
                    'free sulfur dioxide',
                    'total sulfur dioxide',
                    'density',
                    'pH',
                    'sulphates',
                    'alcohol',
                ]
            )
        )

def model():
    global loaded
    global _model
    if loaded:
        return _model
    else:
        models = sorted([m for m in Path(MODEL_PATH).iterdir()], reverse=True)
        with open(models[0], 'rb') as file:
            file.seek(0)
            model = pickle.load(file)
        loaded = True
        _model = model
        return model

@app.post("/predict")
async def predict(data: Vector):
    vector = data.convert().transpose()
    result = model().predict(vector)
    return {'prediction': round(result[0])}
```

Calling the **/predict** endpoint with the following JSON payload will return the predicted winequality.

=== "sample.json"

```json
{
    "fixed_acidity": "10.8",
    "volatile_acidity": "0.28",
    "citric_acid": "0.56",
    "residual_sugar": "2.0",
    "chlorides": "0.075",
    "free_sulfur_dioxide": "17.8",
    "total_sulfur_dioxide": "60.3",
    "density": "0.9980",
    "ph": "3.16",
    "sulphates": "0.58",
    "alcohol": "10"
}
```

The webserver is built as a Docker image with the following Dockerfile:

=== "Dockerfile"

```dockerfile
FROM ubuntu:latest
WORKDIR /app
COPY server.py requirements.txt /app/
RUN apt update && apt install python3 python3-pip -y
RUN pip3 install -r requirements.txt
ENV MODEL_PATH=/app/data/deploy
EXPOSE 3000
ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]
```

The web server should be started with `docker run -d -p 3000:3000 -v $PWD/data/deploy:/app/data/deploy:ro --name model_server model_server`.

#### ETL

The ETL script simply converts the dataset to a feather file with pyArrow.

=== "etl.py"

```python
from pathlib import Path
import sys

from pyarrow import csv
import pyarrow.feather as feather


def load_file(filename: Path):
    table = csv.read_csv(str(filename), parse_options=csv.ParseOptions(delimiter=';'))
    feather_file = f'{filename.stem}.feather'
    feather.write_feather(table, f'{feather_file}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("CSV file path is required.")
        sys.exit(1)
    try:
        fn = Path(sys.argv[1]).resolve()
    except Exception:
        print(f"Cannot load file.")
        sys.exit(1)
    load_file(fn)
```

#### Model Training

The training script reads the feather file, trains the model based on the input parameters, prints the model statistics, and saves the model as a pickle file.

=== "train.py"

```python
from pathlib import Path
import pickle
from decimal import Decimal
import sys
from unicodedata import decimal

import numpy as np
import pandas as pd
import pyarrow.feather as feather
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import ElasticNet


def load(filename: Path) -> pd.DataFrame:
    return feather.read_feather(str(filename))


def save_model(model, filename):
    with open(Path(filename), 'wb') as file:
        pickle.dump(model, file)


def eval_metrics(actual, pred):
    rmse = np.sqrt(mean_squared_error(actual, pred))
    mae = mean_absolute_error(actual, pred)
    r2 = r2_score(actual, pred)
    return rmse, mae, r2


def train_model(df: pd.DataFrame, alpha: Decimal, l1_ratio: Decimal):
    train, test = train_test_split(df, test_size=0.25, train_size=0.75)
    train_x = train.drop(["quality"], axis=1)
    test_x = test.drop(["quality"], axis=1)
    train_y = train[["quality"]]
    test_y = test[["quality"]]

    lr = ElasticNet(alpha=float(alpha), l1_ratio=float(l1_ratio))
    lr.fit(train_x, train_y)

    predicted_qualities = lr.predict(test_x)
    (rmse, mae, r2) = eval_metrics(test_y, predicted_qualities)
    print(f"RMSE: {rmse}")
    print(f" MAE: {mae}")
    print(f"  R2: {r2}")

    return lr


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Parameters file path, alpha, and l1_ratio required.")
        sys.exit(1)
    try:
        fn = Path(sys.argv[1]).resolve()
    except Exception:
        print(f"Cannot load file.")
        sys.exit(1)
    alpha = Decimal(sys.argv[2])
    l1_ratio = Decimal(sys.argv[3])
    data = load(fn)
    model = train_model(data, alpha, l1_ratio)
    pickle_file = f"{fn.stem}.pickle"
    try:
        save_model(model, pickle_file)
    except Exception:
        print(f"Could not save {pickle_file}")
```
