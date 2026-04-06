def flatten_json(嵌套: dict, 连符: str = ".") -> dict:
    果 = {}
    def 步(项, 径=""):
        if isinstance(项, dict):
            for 键, 值 in 项.items(): 步(值, f"{径}{键}{连符}")
        elif isinstance(项, list):
            for 序, 值 in enumerate(项): 步(值, f"{径}{序}{连符}")
        else:
            果[径[:-len(连符)]] = 项
    步(嵌套)
    return 果
