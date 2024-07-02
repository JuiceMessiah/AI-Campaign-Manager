# **AI Campaign Manager**
The official AI Campaign Manager for Filify, providing ease of use for companies, wanting to generate campaigns and message templates for their influencer collaborators. 
This program is part of Filify's toolbelt for streamlining and decreasing friction between companies, wanting to advertise their products, and influencers, eager to collaborate with companies.

## **How It Works:**
When a company signs up with Filify to generate a campaign, they provide a link (URL), and the program automatically scrapes their website for text. This text is then used to prompt ChatGPT to generate an influencer affiliate campaign, along with optional message templates for:
- **Invite**: Message template for inviting an influencer to a given campaign.
- **Welcome**: Message template for welcomming an influencer to a campaign , along with any necessary information on how said influencer is to promote the company's products/services
- **Reject**: Message template for formally rejecting a given influencer from a given campaign.

In the case, that the company already has an affiliate campaign that they want to generate message templates from, then they simply insert their affiliate campaign instead.

The requests are made to an AWS Lambda function, in the form of a JSON object: 

```json
{
  "url": "https://example.com/",
  "mail_type": "string",
  "customer_campaign": "string",
  "lang": "en"
}
```

>[!NOTE]
>The URL is validated with [Pydantic](https://docs.pydantic.dev/latest/), using the following type: ```HttpUrl```. This means that the URL parameter should adhere to the following criteria:
>>_```HttpUrl```: scheme ```http``` or ```https```, TLD required, host required, max length 2083_
> 
>(Excerpt from Pydantic [URL type documentation](https://docs.pydantic.dev/1.10/usage/types/#urls))
>

Here, these three variables are all optional, but adhere to certain conditions. 
1. **URL**(```HttpUrl```): This parameter is optional, and can be sent by itself.
2. **mail_type**(```Literal[str]```): This is also optional, but depends on either an accompanying URL or customer_campaign parameter. (Can't make a mail template without a campaign.)
3. **customer_campaign**(```str```): Only depends on "mail_type", but can't be sent with a URL, since generating a campaign when one is already present is counter-productive.
4. **lang**(```str```): Accepts ```str``` values, in the form of a two-letter abbreviation a given language (I.e. 'da' for 'danish', 'es': 'espanol' etc.) Not case sensitive. Should not be by itself or alone with "mail_type". <br>

This table presents the language abbreviations as headers and their full names in the corresponding row beneath each header.<br>
The languages we support currently are:

| en     | es       | fr        | de      | it       | pt         | ru       | nl         | sv      | no     | da     | fi     | pl     | cs       | el       | hu     | ro     | bg        | hr       | sk         | sl          | lt       | lv       | et    | ga      | mt    |
|--------|----------|-----------|---------|----------|------------|----------|------------|---------|--------|--------|--------|--------|----------|----------|--------|--------|-----------|----------|------------|-------------|----------|----------|-------|---------|-------|
| English| Español  | Français  | Deutsch | Italiano | Português  | Русский  | Nederlands | Svenska | Norsk  | Dansk  | Suomi  | Polski | Čeština  | Ελληνικά | Magyar | Română | Български | Hrvatski | Slovenčina | Slovenščina | Lietuvių | Latviešu | Eesti | Gaeilge (Irish) | Malti |

Note that this also mean that you **cannot** have all four parameters present in a single request. Failing to adhere to any of these conditions will result in a validation error.

## **Installation:**
Here we will outline how to install, set up and run this application on your local machine. 

### **Dependencies:**
**Python:** The application is written in ```Python```. Please navigate to the offical [Python downloads page](https://www.python.org/downloads/). <br>
Ensure Python is correctly installed by running:

- `$ python -V` (should show "Python 3.x.x")
- `$ pip -V`

### **Docker**:
This project uses containerization with ```Docker```. Please install it from the [Docker downloads page](https://www.docker.com/products/docker-desktop/).

### **AWS CLI**:
Used to push ```Docker``` containers to AWS. Please refer to the [AWS CLI Download page](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).  

### **Source Code:**
Next you will need the source code for this project. Please either clone this repository to your local IDE, or just download the entire source code as a .ZIP file. After having successfully downloaded the application, you will need to install the required packages/libraries. To do this, simply run the command:

```sh
$ pip install -r requirements.txt
```

This will install any other dependencies/packages, that is needed for this project to function.

Now you are ready to build and run this project. When it comes to running this application **locally**, you can use ```FastAPI``` in tandem with ```Docker```. 

### **FastAPI:**
When executing this program locally, you can simply press the _Run_ button in your preffered IDE. This will start a local server on your machine, hosted with ```Uvicorn```, in ```http://localhost:8080/```. Here we have **three** distinct endpoints for our application:

- ```/streaming``` (POST): Will stream responses back, Chat-GPT style.
- ```/buffered``` (POST): This will take your prompt, and only deliver the campaign, once it is completely finished.
- ```/test``` (GET): This is a simple test endpoint. Will return a JSON object, along with a small stream of data.

To run this locally, use the following command:

```sh
$ curl --location 'http://localhost:8080/<ENDPOINT>' --header 'Content-Type: application/json' --data '{ "url": "", "mail_type": "", "customer_campaign": "", "lang": ""}'
```

Using FastAPI has the added benefit of having an in-built UI for managing endpoints, schemas and generating cURL commands to your desired endpoints. It is called _Swagger UI_. To access it, navigate to ```http://localhost:8080/docs``` in your browser of choice while your server is running.

### **Using Docker:**
Now we can containerize this application and host it on AWS Lambda. For this step it is important to have ```Docker``` open and running. Here it is a matter of following the official [Documentation](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html). 

Should you already have a Lambda function and an accompanying ECR registry, you can quickly push your changes to the function as such:

1. Authenticate the Docker CLI to your Amazon ECR registry:
```sh
$ aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin <AWS ACCOUNT ID>.dkr.ecr.eu-central-1.amazonaws.com
```

2. Build your ```Docker``` image:
```sh
$ docker build --platform linux/amd64 -t docker-image:test .
```

3. Tag your ```Docker``` image:
```sh
$ docker tag docker-image:test <ECRrepositoryUri>:latest
```

4. Push your ```Docker``` image:
```sh
$ docker push <ECRrepositoryUri>:latest
```

5. Update the code for your AWS Lambda function:
```sh
$ aws lambda update-function-code --function-name <LAMBDA FUNCTION NAME> --image-uri <AWS ACCOUNT ID>.dkr.ecr.eu-central-1.amazonaws.com/test:latest
```

Now your Lambda function code is updated with the your latest code!


>[!TIP]
>If one wants to test the functionality of this program, by itself, simply navigate to your local handy-dandy bash terminal and input the following prompt:
>
>```sh
>curl --location 'https://sujqtqyr4fymo7i75c7zul6oge0fzvzz.lambda-url.eu-central-1.on.aws/<ENDPOINT>' --header 'Content-Type: application/json' --data '{ "url": "", "mail_type": "", "customer_campaign": "", "lang": ""}'
>```
>

>[!NOTE]
>Seeing as the briefs we generate are large, with a complex set of instructions, _and_ we are using an expensive model (```GPT-4o``` at the time of writing this), one should be conscious of token usage while using this bot.
>Also, currently there is no setup for authentication on AWS. This should be set up, such that only Filify can make requests to the bot.
>


