from fastapi import APIRouter, Request, Body
from app.engine import evaluate
from app.web import render
router=APIRouter()
@router.get('/reconcile')
def page(request:Request):
    return render(request,'reconcile')
@router.post('/api/reconcile')
def calculate(payload:dict=Body(default={})):
    return evaluate(payload,until=6)
