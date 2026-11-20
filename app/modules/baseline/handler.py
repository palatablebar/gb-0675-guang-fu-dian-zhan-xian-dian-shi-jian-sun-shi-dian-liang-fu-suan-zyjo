from fastapi import APIRouter, Request, Body
from app.engine import evaluate
from app.web import render
router=APIRouter()
@router.get('/baseline')
def page(request:Request):
    return render(request,'baseline')
@router.post('/api/baseline')
def calculate(payload:dict=Body(default={})):
    return evaluate(payload,until=4)
