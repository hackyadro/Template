import numpy as np

def directed_hausdorff(A, B):
    # A, B: arrays of shape (N,2)
    d = 0.0
    for a in A:
        dmin = min(np.linalg.norm(a - b) for b in B)
        d = max(d, dmin)
    return d

def hausdorff(A, B):
    return max(directed_hausdorff(A,B), directed_hausdorff(B,A))
