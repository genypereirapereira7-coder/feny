import hashlib

from rest_framework import serializers

from apps.documents.models import Document
from apps.documents.validators import validar_arquivo


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = (
            "id", "customer", "category", "file", "original_filename",
            "mime_type", "size_bytes", "checksum_sha256", "uploaded_by",
            "created_at",
        )
        # Metadados derivados do próprio arquivo, calculados no `create()` —
        # nunca aceitos como campo livre do cliente (ARCHITECTURE.md §42:
        # nenhum campo crítico solto pro cliente da API).
        read_only_fields = (
            "id", "original_filename", "mime_type", "size_bytes",
            "checksum_sha256", "uploaded_by", "created_at",
        )

    def validate_file(self, arquivo):
        validar_arquivo(arquivo)
        return arquivo

    def create(self, validated_data):
        arquivo = validated_data["file"]
        conteudo = arquivo.read()
        arquivo.seek(0)

        validated_data["original_filename"] = arquivo.name
        validated_data["mime_type"] = getattr(arquivo, "content_type", "") or "application/octet-stream"
        validated_data["size_bytes"] = arquivo.size
        validated_data["checksum_sha256"] = hashlib.sha256(conteudo).hexdigest()
        validated_data["uploaded_by"] = self.context["request"].user

        return super().create(validated_data)
