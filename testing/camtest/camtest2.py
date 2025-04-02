for i in range(0, 0xF0F0 + 1):
    hex_4 = f"{i:04X}"  # e.g. "1234"
    # Swap the last two bytes => "3412"
    swapped_str = hex_4[2:] + hex_4[:2]  # slice "1234" => "12" + "34" => "3412"
    
    prompt = bytes.fromhex("AA0E0000" + swapped_str)
    print(prompt)
