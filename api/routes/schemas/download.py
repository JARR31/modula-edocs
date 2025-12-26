from marshmallow import Schema, fields, validates, ValidationError


class DownloadRequestSchema(Schema):
    filename = fields.String(required=True, data_key="filename")
    tar_path = fields.String(required=True, data_key="tar_path")

    @validates("filename")
    def _validate_filename(self, value: str):
        if not value or not value.strip():
            raise ValidationError("filename must not be empty")

    @validates("tar_path")
    def _validate_tar_path(self, value: str):
        if not value or not value.strip():
            raise ValidationError("tar_path must not be empty")
