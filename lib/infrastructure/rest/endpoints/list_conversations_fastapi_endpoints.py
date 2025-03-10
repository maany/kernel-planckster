from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError

from lib.core.sdk.fastapi import FastAPIEndpoint
from lib.core.view_model.list_conversations_view_model import ListConversationsViewModel
from lib.infrastructure.config.containers import ApplicationContainer
from lib.infrastructure.controller.list_conversations_controller import ListConversationsControllerParameters

from dependency_injector.wiring import inject, Provide


class ListConversationsFastAPIFeature(
    FastAPIEndpoint[ListConversationsControllerParameters, ListConversationsViewModel]
):
    @inject
    def __init__(
        self,
        descriptor: Any = Provide[ApplicationContainer.list_conversations_feature.feature_descriptor],
        controller: Any = Provide[ApplicationContainer.list_conversations_feature.controller],
    ):
        responses: dict[int | str, dict[str, Any]] = {
            200: {
                "model": ListConversationsViewModel,
                "description": "Success",
            },
            400: {
                "model": ListConversationsViewModel,
                "description": "Bad Request. Research Context ID does not exist",
            },
            500: {
                "model": ListConversationsViewModel,
                "description": "Internal Server Error",
            },
        }

        super().__init__(controller=controller, descriptor=descriptor, responses=responses)

    def register_endpoint(self) -> None:
        @self.router.get(
            name=self.name,
            description=self.descriptor.description,
            path="/research-context/{id}/conversation",
            responses=self.responses,
        )
        def endpoint(
            id: int,
        ) -> ListConversationsViewModel | None:
            try:
                controller_parameters = ListConversationsControllerParameters(
                    research_context_id=id,
                )
            except ValidationError as ve:
                raise HTTPException(status_code=400, detail=ve.errors())
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

            view_model: ListConversationsViewModel = self.execute(
                controller_parameters=controller_parameters,
            )
            return view_model
