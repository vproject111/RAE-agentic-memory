# A simple script with non-descriptive variable names


def process_data(data_list):
    """
    This function processes a list of data.
    """
    for x in range(len(data_list)):
        itm = data_list[x]
        print(f"Processing {itm} at index {x}")


my_data = ["apple", "banana", "cherry"]
process_data(my_data)
