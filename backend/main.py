    limit: Optional[int] = None,
) -> JSONResponse:
    try:
        data = get_incident_investigations(
            severity=severity,
            status_filter=status,
            limit=limit,
        )
        return JSONResponse(status_code=200, content=data)
    except Exception:
        logger.exception("Using demo incident records because Exasol retrieval failed")
        items = DEMO_INCIDENTS[:]
        if severity:
            items = [x for x in items if x["severity"].upper() == severity.upper()]
        if status:
            items = [x for x in items if x["status"].upper() == status.upper()]
        if limit is not None and limit > 0:
            items = items[:limit]
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data_mode": "demo",
                "total": len(items),
                "incidents": items,
                "message": "DEMO DATA: These incidents are illustrative, not live database records.",
            },
        )


@app.get("/api/investigations", tags=["Investigations"])
def list_investigations(
    case_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    try:
        data = get_investigation_cases(
            case_id=case_id,
            severity=severity,
            status=status,
            limit=limit,
        )
        return JSONResponse(status_code=200, content=data)
    except Exception:
        logger.exception("Using demo investigation cases because Exasol retrieval failed")
        return JSONResponse(
            status_code=200,
            content=filtered_demo_investigations(
                case_id=case_id,
                severity=severity,
                status=status,
                limit=limit,
            ),
        )


@app.get("/api/lineage", tags=["Lineage"])
def get_lineage() -> JSONResponse:
    try:
        data = get_lineage_data()
        return JSONResponse(status_code=200, content=data)
    except Exception:
        logger.exception("Using demo lineage because Exasol retrieval failed")
        return JSONResponse(status_code=200, content=DEMO_LINEAGE)


@app.get("/api/quality-checks", tags=["Quality Checks"])
def list_quality_checks(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    dataset: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    try:
        data = get_quality_checks(
            status=status,
            severity=severity,
            dataset=dataset,
            search=search,
            limit=limit,
        )
        return JSONResponse(status_code=200, content=data)
    except Exception:
        logger.exception("Using demo quality checks because Exasol retrieval failed")
        items = DEMO_QUALITY_CHECKS[:]

        if status:
            items = [
                x for x in items
                if status.upper() in (
                    x["status"].upper(), x["check_status"].upper()
                )
            ]
        if severity:
            items = [x for x in items if x["severity"].upper() == severity.upper()]
        if dataset:
            items = [
                x for x in items
                if dataset.lower() in x["dataset_name"].lower()
            ]
        if search:
            items = [
                x for x in items
                if search.lower() in str(x).lower()
            ]
        if limit is not None and limit > 0:
            items = items[:limit]

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data_mode": "demo",
                "total": len(items),
                "quality_checks": items,
                "message": "DEMO DATA: These checks are illustrative, not live database results.",
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
