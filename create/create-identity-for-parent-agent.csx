#!/usr/bin/env dotnet-script

#r "nuget: Spectre.Console, 0.47.0"
#r "nuget: HexaEightAgent, 1.6.846"

using System;
using System.IO;
using System.Threading;
using HexaEightAgent;
using Spectre.Console;

// Configuration constants
const string ENV_FILE = "env-file";

// Parse command line arguments
(string configFile, bool showLogs) ParseArguments(string[] args)
{
    if (args.Length == 0 || args.Length > 2) return ("", false);

    string configFile = "";
    bool showLogs = false;

    foreach (string arg in args)
    {
        if (arg == "--show-logs") showLogs = true;
        else if (!arg.StartsWith("--")) configFile = arg;
    }

    return (configFile, showLogs);
}

void DisplayHeader()
{
    AnsiConsole.Clear();
    AnsiConsole.Write(new Rule("[bold blue]🏢 HexaEight Parent Agent Creator[/]").Centered());
    AnsiConsole.WriteLine();
}

void DisplayUsage()
{
    AnsiConsole.MarkupLine("[red]Usage:[/] dotnet script CreateParentAgent.csx -- [yellow]<config_file>[/] [yellow][[--show-logs]][/]");
    AnsiConsole.MarkupLine("[blue]Example:[/] dotnet script CreateParentAgent.csx -- parent_agent.json --show-logs");
    AnsiConsole.MarkupLine("[blue]Example:[/] dotnet script CreateParentAgent.csx -- parent_agent.json");
    AnsiConsole.WriteLine();
    AnsiConsole.MarkupLine("[yellow]Notes:[/]");
    AnsiConsole.MarkupLine("• Config file will store the parent agent credentials");
    AnsiConsole.MarkupLine("• Only one parent agent per environment is allowed");
    AnsiConsole.MarkupLine("• Requires HEXAEIGHT_CLIENT_ID and HEXAEIGHT_TOKEN_SERVER_URL environment variables");
    AnsiConsole.MarkupLine("• Requires env-file with HexaEight credentials");
}

// ====================================================================
// MAIN SCRIPT EXECUTION
// ====================================================================

DisplayHeader();

// Parse arguments
var (configFile, showLogs) = ParseArguments(Args.ToArray());
if (string.IsNullOrEmpty(configFile))
{
    DisplayUsage();
    return;
}

try
{
    // Check environment variables
    string clientId = Environment.GetEnvironmentVariable("HEXAEIGHT_CLIENT_ID") ?? "";
    string tokenServerUrl = Environment.GetEnvironmentVariable("HEXAEIGHT_TOKEN_SERVER_URL") ?? "";

    if (string.IsNullOrEmpty(clientId) || string.IsNullOrEmpty(tokenServerUrl))
    {
        AnsiConsole.MarkupLine("[red]❌ Missing HEXAEIGHT_CLIENT_ID or HEXAEIGHT_TOKEN_SERVER_URL environment variables[/]");
        AnsiConsole.WriteLine();
        AnsiConsole.MarkupLine("[yellow]💡 Set these environment variables before running:[/]");
        AnsiConsole.MarkupLine("   export HEXAEIGHT_CLIENT_ID=\"your_client_id\"");
        AnsiConsole.MarkupLine("   export HEXAEIGHT_TOKEN_SERVER_URL=\"your_token_server_url\"");
        return;
    }

    AnsiConsole.MarkupLine($"[green]✓[/] Client ID: [cyan]{clientId}[/]");
    AnsiConsole.MarkupLine($"[green]✓[/] Token Server: [cyan]{tokenServerUrl}[/]");
    if (showLogs) AnsiConsole.MarkupLine("[yellow]✓ Debug logging enabled[/]");
    AnsiConsole.WriteLine();

    // Load environment file
    try
    {
        var loadedVars = EnvironmentManager.LoadHexaEightVariablesFromEnvFile(ENV_FILE);
        AnsiConsole.MarkupLine($"[green]✓[/] Loaded {loadedVars.Count} variables from env-file");
    }
    catch (Exception ex)
    {
        AnsiConsole.MarkupLine($"[red]❌ Failed to load env-file: {ex.Message}[/]");
        AnsiConsole.MarkupLine("[yellow]💡 Make sure 'env-file' exists in the current directory with HexaEight credentials[/]");
        return;
    }

    // Check HexaEight credentials
    var (resourceName, machineToken, _, _) = EnvironmentManager.GetAllEnvironmentVariables();
    if (string.IsNullOrEmpty(resourceName) || string.IsNullOrEmpty(machineToken))
    {
        AnsiConsole.MarkupLine("[red]❌ Missing HEXAEIGHT_RESOURCENAME or HEXAEIGHT_MACHINETOKEN in env-file[/]");
        AnsiConsole.WriteLine();
        AnsiConsole.MarkupLine("[yellow]💡 Your env-file should contain:[/]");
        AnsiConsole.MarkupLine("   HEXAEIGHT_RESOURCENAME=your_resource_name");
        AnsiConsole.MarkupLine("   HEXAEIGHT_MACHINETOKEN=your_machine_token");
        return;
    }

    AnsiConsole.MarkupLine($"[green]✓[/] Resource Name: [cyan]{resourceName}[/]");
    AnsiConsole.WriteLine();

    // Check if parent agent already exists
    if (File.Exists(configFile))
    {
        bool overwrite = AnsiConsole.Confirm($"[yellow]⚠ Parent agent config '{configFile}' already exists. Overwrite?[/]");
        if (!overwrite)
        {
            AnsiConsole.MarkupLine("[yellow]Operation cancelled.[/]");
            return;
        }
    }

    // Create parent agent
    bool success = false;
    AnsiConsole.Status()
        .Spinner(Spinner.Known.Star)
        .SpinnerStyle(Style.Parse("green"))
        .Start("Creating parent agent...", ctx =>
        {
            ctx.Status("Initializing agent configuration...");
            var agentConfig = new AgentConfig();
            if (showLogs) agentConfig.EnableDebugMode();
            
            ctx.Status("Setting up client credentials...");
            Thread.Sleep(500);
            
            ctx.Status("Creating parent agent identity...");
            success = agentConfig.CreateAIParentAgent(configFile, true, clientId, tokenServerUrl, showLogs);
        });

    AnsiConsole.WriteLine();
    if (success)
    {
        var successTable = new Table()
            .Border(TableBorder.Double)
            .Title("[bold green]🎉 Parent Agent Created Successfully[/]")
            .AddColumn("[bold]Property[/]")
            .AddColumn("[bold]Value[/]");

        successTable.AddRow("🏢 Agent Type", "[magenta]Parent Agent[/]");
        successTable.AddRow("📁 Config File", $"[yellow]{configFile}[/]");
        successTable.AddRow("🌐 Resource Name", $"[cyan]{resourceName}[/]");
        successTable.AddRow("🌐 Token Server", $"[blue]{tokenServerUrl}[/]");
        successTable.AddRow("🔧 Client ID", $"[dim]{clientId}[/]");
        successTable.AddRow("✅ Status", "[green]Active & Ready[/]");

        AnsiConsole.Write(successTable);

        AnsiConsole.WriteLine();
        AnsiConsole.Write(
            new Panel(
                $"[green]✅ Parent agent created successfully![/]\n\n" +
                $"[bold]Capabilities:[/]\n" +
                $"• Create unlimited child agents\n" +
                $"• JWT token creation & validation\n" +
                $"• Message encryption/decryption\n" +
                $"• Secure communication with other parent agents\n\n" +
                $"[bold]Next Steps:[/]\n" +
                $"• Use CreateChildAgent.csx to create child agents\n" +
                $"• Use LoadParentAgent.csx to load this agent\n" +
                $"• Configuration saved in: [cyan]{configFile}[/]")
            .Header("🚀 Success!")
            .Border(BoxBorder.Double)
            .BorderColor(Color.Green));
    }
    else
    {
        AnsiConsole.Write(
            new Panel($"[red]✗ Failed to create parent agent[/]\n" +
                     "[dim]Check your environment configuration and credentials[/]")
            .Header("❌ Creation Failed")
            .Border(BoxBorder.Heavy)
            .BorderColor(Color.Red));
        
        AnsiConsole.WriteLine();
        AnsiConsole.MarkupLine("[yellow]💡 Troubleshooting tips:[/]");
        AnsiConsole.MarkupLine("• Verify your env-file contains correct HexaEight credentials");
        AnsiConsole.MarkupLine("• Check network connectivity to the token server");
        AnsiConsole.MarkupLine("• Ensure resource name and machine token are valid");
    }
}
catch (Exception ex)
{
    AnsiConsole.WriteException(ex);
    AnsiConsole.MarkupLine($"[red]❌ Unexpected error: {ex.Message}[/]");
}

AnsiConsole.WriteLine();
AnsiConsole.MarkupLine("[dim]Press any key to exit...[/]");
Console.ReadKey(true);
