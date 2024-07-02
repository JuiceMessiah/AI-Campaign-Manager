from pydantic import BaseModel, HttpUrl, model_validator, Field, field_validator
from typing import Optional, Literal, Any
from typing_extensions import Self

languages = {"en": "English", "es": "Español", "fr": "Français", "de": "Deutsch", "it": "Italiano",
             "pt": "Português", "ru": "Русский", "nl": "Nederlands", "sv": "Svenska", "no": "Norsk",
             "da": "Dansk", "fi": "Suomi", "pl": "Polski", "cs": "Čeština", "el": "Ελληνικά", "hu": "Magyar",
             "ro": "Română", "bg": "Български", "hr": "Hrvatski", "sk": "Slovenčina", "sl": "Slovenščina",
             "lt": "Lietuvių", "lv": "Latviešu", "et": "Eesti", "ga": "Gaeilge", "mt": "Malti"}


class QueryRequest(BaseModel):
    url: Optional[HttpUrl] = Field(None, description="The HTTP URL that you wish to base your affiliate "
                                                     "campaign on.")
    mail_type: Optional[Literal['invite', 'welcome', 'reject']] = Field(None, max_length=7, description="The type of mail template, that you would like to generate with your brief.")
    customer_campaign: Optional[str] = Field(None, description="If the customer already has an affiliate "
                                                               "campaign, put it here.")
    lang: Optional[str] = Field("en", max_length=2, validate_default=True,
                                description="The language that you would like your affiliate brief or mail in.")

    # Pydantic decorator for validating models.
    # See https://docs.pydantic.dev/latest/concepts/validators/#model-validators
    @classmethod
    @model_validator(mode='before')
    def check_parameters(cls, data: Any) -> Any:
        """Check parameters in request, should adhere to the right types."""
        if isinstance(data, dict):
            assert (
                    'url' or 'customer_campaign' in data
            ), 'Please provide a URL or a campaign'
            return data

    @model_validator(mode='after')
    def validate_pairs(self) -> Self:
        """Check pairs in request. URL and monitor can't both be present, when proxy is absent.
        Monitor and proxy also can't be present without a URL.

        For more info please consult the README: https://github.com/Filify-app/ai-campaign-manager.
        """
        url = self.url
        mail_type = self.mail_type
        customer_campaign = self.customer_campaign

        # Validation conditions. Certain pairs of values cannot be present with eachother. See README for details.
        if url and customer_campaign and not mail_type:
            raise ValueError("Please provide Either a campaign or URL, not both.\n")
        if mail_type and not url and not customer_campaign:
            raise ValueError("mail_type can't be by itself. Please provide either a campaign or URL\n")
        if customer_campaign and not mail_type and not url:
            raise ValueError("The provided campaign can't be processed without a mail_type.\n")
        if url and mail_type and customer_campaign:
            raise ValueError("All three variables can't be present at the same time.\n")

        # Setting default values for any blank parameters.
        self.url = url if url is not None else 'default_url'
        self.mail_type = mail_type if mail_type is not None else 'default_mail_type'
        self.customer_campaign = customer_campaign if customer_campaign is not None else 'default_customer_campaign'

        return self

    @classmethod
    @field_validator('mail_type')
    def validate_mail_type(cls, mail: str):
        # Check if mail_type contains 'invite', 'welcome' or 'reject'.
        if mail and mail not in ['invite', 'welcome', 'reject']:
            raise ValueError(f"Invalid mail_type {mail}. "
                             f"Please provide a valid mail_type: 'invite', 'welcome' or 'reject'.\n")
        else:
            return mail

    @field_validator('lang', mode='after')
    @classmethod
    def validate_language(cls, language: str) -> str:
        if language:
            if language.lower() not in languages:
                raise ValueError(f"Unsupported language: '{language}', Please try another.\n")
            else:
                language_val = languages[language.lower()]
                return language_val
