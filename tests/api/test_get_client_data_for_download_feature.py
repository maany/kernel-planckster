import os
import random

import requests
from lib.core.usecase.get_client_data_for_download_usecase import GetClientDataForDownloadUseCase
from lib.core.usecase_models.get_client_data_for_download_usecase_models import (
    GetClientDataForDownloadRequest,
    GetClientDataForDownloadResponse,
)
from lib.core.view_model.get_client_data_for_download_view_model import GetClientDataForDownloadViewModel
from lib.infrastructure.config.containers import ApplicationContainer
from lib.infrastructure.presenter.get_client_data_for_download_presenter import GetClientDataForDownloadPresenter
from lib.infrastructure.repository.minio.models import MinIOPFN
from lib.infrastructure.repository.sqla.database import TDatabaseFactory
from lib.infrastructure.repository.sqla.models import SQLAClient, SQLASourceData


def test_get_client_data_for_download_feature(
    app_container: ApplicationContainer,
    test_file_path: str,
    fake_client_with_source_data: SQLAClient,
    db_session: TDatabaseFactory,
) -> None:
    presenter: GetClientDataForDownloadPresenter = app_container.get_client_data_for_download_feature.presenter()
    usecase: GetClientDataForDownloadUseCase = app_container.get_client_data_for_download_feature.usecase()

    assert presenter is not None
    assert usecase is not None

    file_path = test_file_path

    sqla_client = fake_client_with_source_data
    sqla_source_data = random.choice(sqla_client.source_data)

    with db_session() as session:
        session.add(sqla_client)
        session.commit()

        # Manually upload file
        minio_file_repo = app_container.minio_file_repository()
        minio_store = minio_file_repo.store

        bucket_name = MinIOPFN.process_bucket_name(sqla_client.sub)

        pfn = minio_store.protocol_and_relative_path_to_pfn(
            protocol=sqla_source_data.protocol,
            relative_path=sqla_source_data.relative_path,
            bucket_name=bucket_name,
        )
        minio_object = minio_store.pfn_to_object_name(pfn)

        minio_file_repo.store.create_bucket_if_not_exists(minio_object.bucket_name)
        minio_store.client.fput_object(
            bucket_name=minio_object.bucket_name, object_name=minio_object.object_name, file_path=file_path
        )

        # Now ask for the download information using the usecase
        request = GetClientDataForDownloadRequest(
            client_id=sqla_client.id,
            protocol=sqla_source_data.protocol,
            relative_path=sqla_source_data.relative_path,
        )
        response = usecase.execute(request=request)

        assert response is not None
        assert response.status == True
        assert isinstance(response, GetClientDataForDownloadResponse)

        view_model = presenter.convert_response_to_view_model(response=response)

        assert view_model is not None
        assert isinstance(view_model, GetClientDataForDownloadViewModel)
        assert view_model.status == True

        assert view_model.signed_url

        signed_url = view_model.signed_url

        # Now test that the signed_url actually works
        out_file_path = f"{file_path}.downloaded"

        try:
            download_res = requests.get(signed_url)
            with open(out_file_path, "wb") as f:
                f.write(download_res.content)

            # Read both files and assert they're the same
            with open(file_path, "rb") as f:
                original_content = f.read()

            with open(out_file_path, "rb") as f:
                downloaded_content = f.read()

            assert original_content == downloaded_content

        finally:
            # Clean up
            os.remove(out_file_path)
            os.remove(file_path)
