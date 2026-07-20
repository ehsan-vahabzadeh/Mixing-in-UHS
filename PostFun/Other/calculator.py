
class Calculator:
    
    def tokenizer(expr_str):
        ch_list = []
        ch_type =[]
        building_number = False # Indicator for digit whether it is a num or not
        unary_check = False # Indicator for number if it a unary one
        for ch in expr_str:
            if ch == " ":
                continue
            if (ch.isdigit() and building_number) or (ch == "." and building_number): 
                ch_list[- 1] += ch   
            elif ch.isdigit() and building_number == False:
                if unary_check:
                    ch = "-" + ch
                    unary_check = False
                ch_list.append(ch)
                ch_type.append("num")
            elif ch =="." and building_number == False:
                ch_list.append(ch)
            elif ch in "+-*/":
                if (ch == "-" and len(ch_list) == 0) or (ch == "-" and ch_list[-1] in "+-*/"):
                    unary_check = True
                    continue
                ch_list.append(ch)
                ch_type.append("OP")
            elif ch == "(":
                if unary_check:
                    temp_ch = "-1"
                    unary_check = False
                    ch_list.append(temp_ch)
                    ch_type.append("num")
                    ch_list.append("*")
                    ch_type.append("OP")
                ch_list.append(ch)
                ch_type.append("LPAR")
            elif ch == ")":
                ch_list.append(ch)
                ch_type.append("RPAR")    
            else:
                raise ValueError(f"Invalid character: {ch}")
            if ch.isdigit() or ch == ".":
                building_number = True
            else:
                building_number = False
        # ch_list = float(ch_list)
        return ch_list, ch_type
    
    def validate(tokens,token_type):
        len_token = len(token_type)
        P_balance = 0
        RP_check = False
        if token_type.count("LPAR") != token_type.count("RPAR"):
            raise ValueError(f"You have on extra/less parantheses")
        dot_check = False
        for index,t in enumerate(token_type[:-1]):
            if token_type[index] == "dot" and token_type[index+1] == "dot":
                raise ValueError(f"You have 2 successive dots (..)")
            if token_type[index] == "num" and token_type[index+1] == "num":
                raise ValueError(f"You are missing an operator.")  
            if token_type[index] == "num" and token_type[index+1] == "LPAR":
                    raise ValueError(f"You are missing an operator.")  
            if token_type[index] == "LPAR":
                P_balance += 1 
            if token_type[index] == "RPAR":
                P_balance -= 1
            if P_balance < 0:    
                raise ValueError(f"Sequence of Parantheses is not followed correctly")     
        return 0
    def precedence(ch):
        if ch in "*/":
            return 2
        elif ch in "+-":
            return 1
        else:
            return 0
        
    def priority(tokens, token_type):
        output =[]
        stack = []
        for index, t in enumerate(token_type):
            if t == "num":
                output.append(tokens[index])
            elif t == "LPAR":
                stack.append("LPAR")
            elif t == "RPAR":
                id_LPAR = True
                while id_LPAR:
                    if stack[-1] != "LPAR":
                     output.append(stack.pop())
                    else:
                        id_LPAR = False
                stack.pop()
            elif t == "OP":
                # pop operators with higher or equal precedence (stop at LPAR)
                while len(stack) > 0 and stack[-1] != "LPAR":
                    prec_prev = Calculator.precedence(stack[-1])
                    prec_curr = Calculator.precedence(tokens[index])

                    if prec_prev >= prec_curr:   # left-associative operators
                        output.append(stack.pop())
                    else:
                        break

                # push current operator
                stack.append(tokens[index])
        while stack:
            output.append(stack.pop())
        return output 
    def eval(order):
        stuck = []
        ans = 0
        for el in order:
            if el in "+-*/":
                a = stuck.pop()
                b = stuck.pop()
                if(el == "+"):
                    ans = a + b        
                elif(el == "*"):
                    ans = a * b
                elif(el == "/"):
                    ans = b / a
                elif(el == "-"):
                    ans = b - a    
                stuck.append(float(ans))
            else: 
                stuck.append(float(el))
        
        return ans
if __name__ == "__main__":
    quit = False
    while (quit == False):
        inp_str = input("Enter an expression: \n")
        if (inp_str == "quit"):
            quit = True
            continue
        tokens, token_type = Calculator.tokenizer(inp_str)
        Calculator.validate(tokens,token_type)
        order = Calculator.priority(tokens, token_type)
        output = Calculator.eval(order)
        print(output)
  