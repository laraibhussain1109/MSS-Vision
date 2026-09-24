"""Reusable ROI geometry helpers for future handle-based scene editors."""
def clamp_points(points): return [[max(0.0,min(1.0,x)),max(0.0,min(1.0,y))] for x,y in points]
def translated(points,dx,dy): return clamp_points([[x+dx,y+dy] for x,y in points])
