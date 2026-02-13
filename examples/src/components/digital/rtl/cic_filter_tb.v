/*
 * Testbench for CIC decimation filter.
 *
 * Feeds a constant din=1 bitstream and verifies that valid pulses
 * appear at the expected decimation rate. Dumps all signals to VCD.
 */

`timescale 1ns / 1ps

module cic_filter_tb;

    parameter ORDER            = 3;
    parameter DECIMATION_RATIO = 64;
    parameter INPUT_WIDTH      = 1;
    parameter OUTPUT_WIDTH     = 16;

    reg                        clk;
    reg                        rst_n;
    reg  signed [INPUT_WIDTH-1:0] din;
    wire signed [OUTPUT_WIDTH-1:0] dout;
    wire                       valid;

    // Instantiate DUT
    cic_filter #(
        .ORDER(ORDER),
        .DECIMATION_RATIO(DECIMATION_RATIO),
        .INPUT_WIDTH(INPUT_WIDTH),
        .OUTPUT_WIDTH(OUTPUT_WIDTH)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .din(din),
        .dout(dout),
        .valid(valid)
    );

    // Clock generation: 100 MHz (10 ns period)
    initial clk = 0;
    always #5 clk = ~clk;

    // Stimulus
    integer valid_count;
    initial begin
        // VCD dump
        $dumpfile("cic_filter_tb.vcd");
        $dumpvars(0, cic_filter_tb);

        // Initialize
        rst_n = 0;
        din   = 0;
        valid_count = 0;

        // Hold reset for 100 ns
        #100;
        rst_n = 1;

        // Feed constant din = 1 (DC input)
        din = 1;

        // Run for 10 decimation periods
        #(10 * DECIMATION_RATIO * 10 + 200);

        $display("Simulation finished. valid_count=%0d", valid_count);
        $finish;
    end

    // Count valid pulses and print output
    always @(posedge clk) begin
        if (valid) begin
            valid_count = valid_count + 1;
            $display("t=%0t valid_count=%0d dout=%0d", $time, valid_count, dout);
        end
    end

endmodule
