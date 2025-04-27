#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging
import hashlib
import uuid
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer
from scoring_api.scoring import get_score, get_interests

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}
DATE_FORMAT = "%d.%m.%Y"


class ValidationError(ValueError):
    pass


class Field:
    def __init__(self, required=False, nullable=False) -> None:
        self.required = required
        self.nullable = nullable

    def validate(self, value):
        raise NotImplementedError

    def __str__(self):
        return f"Field(required={self.required}, nullable={self.nullable})"


class CharField(Field):
    def validate(self, value):
        if not isinstance(value, str):
            raise ValidationError("Value should be a string")


class ArgumentsField(Field):
    def validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError("Value must be a dictionary (JSON object)")


class EmailField(CharField):
    def validate(self, value):
        super().validate(value)

        parts = value.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValidationError("Email must be in the format 'localpart@domainpart'")


class PhoneField(Field):
    def validate(self, value):
        if not isinstance(value, (str, int)):
            raise ValidationError("Phone must be a string or an integer")

        phone_num = str(value)

        if len(phone_num) != 11:
            raise ValidationError("Phone must be contain exactly 11 digits")

        if not phone_num.startswith("7"):
            raise ValidationError("Phone number must start with digit 7")


class DateField(Field):
    def validate(self, value):
        if not isinstance(value, str):
            raise ValidationError("Date must be a string")

        try:
            datetime.strptime(value, DATE_FORMAT)
        except ValueError:
            raise ValidationError(
                f"Date must be in the format '{DATE_FORMAT}' (e.g., 'dd.mm.yyyy')"
            )


class BirthDayField(DateField):
    def validate(self, value):
        super().validate(value)

        try:
            bitrhday_dt = datetime.strptime(value, DATE_FORMAT)
        except ValueError:
            raise ValidationError(f"Invalid birthday date format: {value}")

        today = date.today()
        seventy_years_ago = today - relativedelta(years=70)
        if bitrhday_dt.date() <= seventy_years_ago:
            raise ValidationError(
                "Age must be less than 70 years (birthday cannot be 70 years ago or earlier)"
            )


class GenderField(Field):
    def validate(self, value):
        if value not in GENDERS:
            raise ValidationError(
                "Gender must be one of 0 (Unknown), 1 (Male), or 2 (Female)"
            )


class ClientIDsField(Field):
    def validate(self, value):
        if not isinstance(value, list):
            raise ValidationError("Client IDs must be a list")

        if not value:  # An empty list evaluates to False
            raise ValidationError("Client IDs list cannot be empty")

        if not all(isinstance(element, int) for element in value):
            raise ValidationError("All elements in Client IDs list must be integers")


class BaseRequest(object):
    def __init__(self, data):
        self.errors = {}
        self._raw_data = data or {}

        fields = []
        for name, obj in self.__class__.__dict__.items():
            if isinstance(obj, Field):
                fields.append((name, obj))

        for field_name, field_instance in fields:
            value = data.get(field_name)

            if field_name not in data:
                if field_instance.required:
                    self.errors[field_name] = "This field is requeired"
                continue

            if value is None:
                if not field_instance.nullable:
                    self.errors[field_name] = "This field cannot be null"
                continue

            try:
                field_instance.validate(value)
                setattr(self, field_name, value)
            except ValidationError as e:
                self.errors[field_name] = str(e)

        if not self.errors:
            self.post_validate()

    def post_validate(self):
        """
        Hook method for subclasses to implement cross-field validation.
        This is called only if individual field validation passes.
        Access validated data via self attributes (e.g., self.phone).
        Add errors to self.errors if validation fails.
        """
        pass

    @property
    def is_valid(self):
        """Checks if the request passed validation."""
        return not self.errors

    def get_errors(self):
        """Returns a dictionary of validation errors."""
        return self.errors

    def get_non_empty_fields(self):
        """Helper to get fields that were present and not None"""
        non_empty = []
        for name, obj in self.__class__.__dict__.items():
            if isinstance(obj, Field):
                if name in self.__dict__:
                    value = self.__dict__[name]
                    if value is not None and value != "" and value != []:
                        non_empty.append(name)
        return non_empty


class ClientsInterestsRequest(BaseRequest):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(BaseRequest):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def post_validate(self):
        has_phone = "phone" in self.__dict__
        has_email = "email" in self.__dict__
        has_fname = "first_name" in self.__dict__
        has_lname = "last_name" in self.__dict__
        has_bday = "birthday" in self.__dict__
        has_gender = "gender" in self.__dict__

        pair_1 = has_phone and has_email
        pair_2 = has_fname and has_lname
        pair_3 = has_gender and has_bday

        if not (pair_1 or pair_2 or pair_3):
            self.errors["arguments"] = (
                "At least one pair is required: (phone, email), (first_name, last_name), or (birthday, gender)."
            )


class MethodRequest(BaseRequest):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request: MethodRequest):
    login = getattr(request, "login", None)
    account = getattr(request, "account", None)
    token = getattr(request, "token", None)

    if login is None or token is None:
        return False

    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        account_str = account if account is not None else ""
        digest = hashlib.sha512(
            (account_str + login + SALT).encode("utf-8")
        ).hexdigest()
    return digest == token


def method_handler(request, ctx, store):
    response, code = None, None

    # 1. Validate the base request structure
    method_req = MethodRequest(request.get("body"))
    if not method_req.is_valid:
        first_error = list(method_req.get_errors().items())[0]
        error_msg = f"Validation Error in field '{first_error[0]}': {first_error[1]}"
        return error_msg, INVALID_REQUEST  # 422

    # 2. Check auth
    if not check_auth(method_req):
        return ERRORS[FORBIDDEN], FORBIDDEN  # 403

    # 3. Process based on method name
    method_name = method_req.method
    arguments = method_req.arguments

    if method_name == "online_score":
        score_req = OnlineScoreRequest(arguments)
        if not score_req.is_valid:
            first_error = list(score_req.get_errors().items())[0]
            error_msg = f"Validation Error in arguments for '{method_name}': Field '{first_error[0]}' - {first_error[1]}"
            return error_msg, INVALID_REQUEST  # 422

        ctx["has"] = score_req.get_non_empty_fields()

        # Get score (handle admin case)
        if method_req.is_admin:
            response = {"score": 42}
        else:
            score = get_score(
                store=store,
                phone=getattr(score_req, "phone", None),
                email=getattr(score_req, "email", None),
                birthday=getattr(score_req, "birthday", None),
                gender=getattr(score_req, "gender", None),
                first_name=getattr(score_req, "first_name", None),
                last_name=getattr(score_req, "last_name", None),
            )
            response = {"score": score}
        code = OK  # 200

    elif method_name == "clients_interests":
        interest_req = ClientsInterestsRequest(arguments)
        if not interest_req.is_valid:
            first_error = list(interest_req.get_errors().items())[0]
            error_msg = f"Validation Error in arguments for '{method_name}': Field '{first_error[0]}' - {first_error[1]}"
            return error_msg, INVALID_REQUEST  # 422

        ctx["nclients"] = len(interest_req.client_ids)

        # Get score (handle admin case)
        if method_req.is_admin:
            response = {"score": 42}

        # Get interests
        interests = {}
        for cid in interest_req.client_ids:
            interests[str(cid)] = get_interests(store=store, cid=cid)
        response = interests
        code = OK  # 200

    else:
        return "Method not found", NOT_FOUND  # 404

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {"method": method_handler}
    store = None

    def get_request_id(self, headers):
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request_body = None
        data_string = ""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                data_string = self.rfile.read(content_length)
                request_body = json.loads(data_string)
            else:
                code = BAD_REQUEST
                logging.error(f"Empty request body received. {context['request_id']}")

        except (json.JSONDecodeError, ValueError):  # More specific exceptions
            code = BAD_REQUEST
            logging.error(f"Failed to parse JSON. {context['request_id']}")
        except Exception as e:
            # Catch other potential errors during read/parse
            code = INTERNAL_ERROR
            logging.exception(
                f"Error reading/parsing request body: {e}. {context['request_id']}"
            )

        if request_body is not None and code == OK:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request_body, "headers": self.headers},
                        context,
                        self.store,
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
                    response = "Internal Server Error"
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            error_msg = (
                response
                if isinstance(response, str)
                else ERRORS.get(code, "Unknown Error")
            )
            r = {"error": error_msg, "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))
        return


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()
    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )
    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info("Starting server at %s" % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
