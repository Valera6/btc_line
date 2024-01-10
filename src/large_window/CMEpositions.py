import requests, tempfile, json, os

tempdir = os.path.join(tempfile.gettempdir(), 'BTCline')
settings = json.load(open(os.path.join(tempdir,'settings.json'), 'r'))

response = requests.get("https://www.cftc.gov/dea/futures/financial_lf.htm")

lines = response.text.splitlines()
for num_s, s in  enumerate(lines):
    if (s.find('#133741') != -1):
        global start_i
        start_i = num_s
        line_positions = lines[num_s+2]
        line_changeFrom = lines[num_s+5]
        break

def find_date():
    global start_i
    line = lines[start_i-7]
    for i, char in enumerate(line):
        if line[i:i+5] == 'as of':
            from_date = line[i+6:i+14]
    return from_date
    

positions_line = lines[start_i+2]
change_line = lines[start_i+5]

def collect(index):
    def get_values(line):
        return [int(v.replace(',', '')) for v in line.split(' ') if v!='']
    p_numbers = get_values(positions_line)
    c_numbers = get_values(change_line)

    positions = (p_numbers[index], p_numbers[index+1])
    change = (c_numbers[index], c_numbers[index+1])

    return positions, change

institutional = collect(3)
leveraged_funds = collect(6)
def format(numbers):
    def show_change(index):
        return f"{numbers[0][index]}{numbers[1][index]:+}"
    
    long = show_change(0) if settings['comparison_limit'] else str(numbers[0][0])
    short = show_change(1) if settings['comparison_limit'] else str(numbers[0][1])
    return f"({long}, {short})"

from_date = find_date()
out_str = f"__CME positions; {from_date}:\n"
out_str += format(institutional) + ' ' + format(leveraged_funds)

large_window_config = json.load(open(os.path.join(tempdir, 'large_window.json'), 'r'))
large_window_config['CMEpositions'] = out_str
json.dump(large_window_config, open(os.path.join(tempdir, 'large_window.json'), 'w')) 
