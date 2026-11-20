from fastapi import APIRouter, Request, Body
from app.engine import evaluate
from app.web import render
router=APIRouter()
@router.get('/loss')
def page(request:Request):
    return render(request,'loss')
@router.post('/api/loss')
def calculate(payload:dict=Body(default={})):
    return evaluate(payload,until=5)
