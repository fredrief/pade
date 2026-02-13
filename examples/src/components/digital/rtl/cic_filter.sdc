# CIC filter timing constraints
# Clock: 100 MHz (10 ns period) on port clk
create_clock -name clk -period 10.0 [get_ports clk]

# Input delay: 2 ns after clock edge
set_input_delay -clock clk 2.0 [get_ports {din rst_n}]

# Output delay: 2 ns before clock edge
set_output_delay -clock clk 2.0 [get_ports {dout valid}]
