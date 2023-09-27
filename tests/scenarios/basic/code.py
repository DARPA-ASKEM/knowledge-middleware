# SIR model dynamics definition
def sir(
    s: float, i: float, r: float, beta: float, gamma: float, n: float
) -> Tuple[float, float, float]:
    """The SIR model, one time step."""
    s_n = (-beta * s * i) + s
    i_n = (beta * s * i - gamma * i) + i
    r_n = gamma * i + r
    scale = n / (s_n + i_n + r_n)
    return s_n * scale, i_n * scale, r_n * scale


if __name__ == "main":
    # run sir model sample
    result = sir(0.99, 0.01, 0, 0.2, 0.1, 1)

    print(result)
