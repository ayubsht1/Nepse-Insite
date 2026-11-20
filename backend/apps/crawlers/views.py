import logging

from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from common.events import broadcast_on_commit
from common.permissions import IsAdminRole
from .github_actions import WorkflowDispatchError, dispatch_crawl_workflow
from .models import CrawlRun, CrawlSource
from .serializers import CrawlRunSerializer, CrawlSourceSerializer

logger = logging.getLogger(__name__)


class CrawlSourceViewSet(viewsets.ModelViewSet):
    queryset = CrawlSource.objects.all()
    serializer_class = CrawlSourceSerializer
    permission_classes = [IsAdminRole]
    search_fields = ["name", "key", "base_url"]
    ordering_fields = ["name", "enabled", "created_at"]
    filterset_fields = ["enabled"]


class StartCrawlView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        runs = CrawlRun.objects.select_related("source", "triggered_by")
        if status := request.query_params.get("status"):
            runs = runs.filter(status=status)
        if source_id := request.query_params.get("source"):
            if not source_id.isdecimal():
                raise serializers.ValidationError(
                    {"source": "Source ID must be a positive integer."}
                )
            runs = runs.filter(source_id=source_id)
        page = self.paginate_queryset(runs)
        serializer = CrawlRunSerializer(page if page is not None else runs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def post(self, request):
        source_ids = request.data.get("source_ids")
        if source_ids is not None and (
            not isinstance(source_ids, list)
            or any(not isinstance(value, int) for value in source_ids)
        ):
            raise serializers.ValidationError(
                {"source_ids": "Provide a list of integer source IDs."}
            )
        sources = CrawlSource.objects.filter(enabled=True)
        if source_ids:
            sources = sources.filter(id__in=source_ids)
        sources = list(sources)
        if source_ids and len(sources) != len(set(source_ids)):
            raise serializers.ValidationError(
                {"source_ids": "One or more sources do not exist or are disabled."}
            )
        if not sources:
            raise serializers.ValidationError(
                {"source_ids": "No enabled crawl sources are configured."}
            )

        runs = [
            CrawlRun.objects.create(
                source=source,
                triggered_by=request.user,
                status=CrawlRun.Status.QUEUED,
            )
            for source in sources
        ]
        for run in runs:
            broadcast_on_commit(
                "crawl.run.updated",
                {
                    "run_id": run.pk,
                    "source": run.source.key,
                    "status": run.status,
                },
            )

        try:
            dispatch_crawl_workflow([run.pk for run in runs])
        except WorkflowDispatchError as exc:
            logger.warning("Could not dispatch crawl workflow: %s", exc)
            for run in runs:
                run.status = CrawlRun.Status.FAILED
                run.error_message = str(exc)[:4000]
                run.finished_at = timezone.now()
                run.save(
                    update_fields=["status", "error_message", "finished_at"]
                )
                broadcast_on_commit(
                    "crawl.run.updated",
                    {
                        "run_id": run.pk,
                        "source": run.source.key,
                        "status": run.status,
                    },
                )
            return Response(
                {
                    "runs": CrawlRunSerializer(runs, many=True).data,
                    "error": str(exc),
                },
                status=503,
            )
        return Response({"runs": CrawlRunSerializer(runs, many=True).data}, status=202)

    def paginate_queryset(self, queryset):
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 25
        self._paginator = paginator
        return paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        return self._paginator.get_paginated_response(data)


class CrawlRunDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, _request, pk):
        from django.shortcuts import get_object_or_404

        run = get_object_or_404(
            CrawlRun.objects.select_related("source", "triggered_by"), pk=pk
        )
        return Response(CrawlRunSerializer(run).data)
