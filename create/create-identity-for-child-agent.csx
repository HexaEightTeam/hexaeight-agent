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
const int MIN_PASSWORD_LENGTH = 32;

// Parse command line arguments
(string childName, bool showLogs, string parentConfig) ParseArguments(string[] args)
{
    if (args.Length == 0 || args.Length > 3) return ("", false, "");

    string childName = "";
    bool showLogs = false;
    string parentConfig = "parent_agent.json"; // Default
    var positionalArgs = new List<string>();

    // First pass: extract flags and positional arguments
    foreach (string arg in args)
    {
        if (arg == "--show-logs")
            showLogs = true;
        else if (!arg.StartsWith("--"))
            positionalArgs.Add(arg);
    }

    // Parse positional arguments
    if (positionalArgs.Count >= 1)
        childName = positionalArgs[0];

    if (positionalArgs.Count >= 2)
        parentConfig = positionalArgs[1];

    return (childName, showLogs, parentConfig);
}

void DisplayHeader()
{
    AnsiConsole.Clear();
    AnsiConsole.Write(new Rule("[bold magenta]👥 HexaEight Child Agent Creator[/]").Centered());
    AnsiConsole.WriteLine();
}

void DisplayUsage()
{
    AnsiConsole.MarkupLine("[red]Usage:[/] dotnet script CreateChildAgent.csx -- [yellow]<child_name>[/] [yellow][[--show-logs]][/] [yellow][[parent_config_file]][/]");
    AnsiConsole.MarkupLine("[blue]Example:[/] dotnet script CreateChildAgent.csx -- Finance --show-logs");
    AnsiConsole.MarkupLine("[blue]Example:[/] dotnet script CreateChildAgent.csx -- HR custom_parent.json");
    AnsiConsole.MarkupLine("[blue]Example:[/] dotnet script CreateChildAgent.csx -- \"IT-Support\" --show-logs my_parent.json");
    AnsiConsole.MarkupLine("[blue]Example:[/] dotnet script CreateChildAgent.csx -- Finance");
    AnsiConsole.WriteLine();
    AnsiConsole.MarkupLine("[yellow]Parameters:[/]");
    AnsiConsole.MarkupLine("• [cyan]child_name[/] - Name for the child agent (required)");
    AnsiConsole.MarkupLine("• [cyan]--show-logs[/] - Enable debug logging (optional)");
    AnsiConsole.MarkupLine("• [cyan]parent_config_file[/] - Parent agent config file (optional, defaults to 'parent_agent.json')");
    AnsiConsole.WriteLine();
    AnsiConsole.MarkupLine("[yellow]Notes:[/]");
    AnsiConsole.MarkupLine("• Child name can contain spaces and hyphens");
    AnsiConsole.MarkupLine("• Password must be at least 32 characters");
    AnsiConsole.MarkupLine("• Parent agent must be created first");
    AnsiConsole.MarkupLine("• Requires HEXAEIGHT_CLIENT_ID and HEXAEIGHT_TOKEN_SERVER_URL environment variables");
}

void DisplayChildAgentInfo(string childName, string parentConfigFile)
{
    var infoPanel = new Panel(
        $"[bold]Child Agent Name:[/] [cyan]{childName}[/]\n" +
        $"[bold]Agent Type:[/] Child Agent (Password Protected)\n" +
        $"[bold]Parent Config:[/] [yellow]{parentConfigFile}[/]\n" +
        $"[bold]Parent Required:[/] Yes - will inherit from parent resource\n" +
        $"[bold]Capabilities:[/] Message encryption/decryption within token server\n" +
        $"[bold]Password Security:[/] Minimum {MIN_PASSWORD_LENGTH} characters required")
        .Header("👶 Child Agent Information")
        .Border(BoxBorder.Rounded)
        .BorderColor(Color.Cyan1);

    AnsiConsole.Write(infoPanel);
    AnsiConsole.WriteLine();
}

string GetSecurePassword()
{
    AnsiConsole.Write(
        new Panel($"[yellow]🔐 Password Requirements:[/]\n" +
                 $"• Minimum {MIN_PASSWORD_LENGTH} characters\n" +
                 "• Use a strong, unique password\n" +
                 "• This password will be required to load the child agent")
        .Header("🛡️ Security Requirements")
        .Border(BoxBorder.Rounded)
        .BorderColor(Color.Yellow));

    AnsiConsole.WriteLine();

    while (true)
    {
        string password1 = AnsiConsole.Prompt(
            new TextPrompt<string>($"Enter password (min {MIN_PASSWORD_LENGTH} chars):")
                .Secret());

        if (password1.Length < MIN_PASSWORD_LENGTH)
        {
            AnsiConsole.MarkupLine($"[red]❌ Password must be at least {MIN_PASSWORD_LENGTH} characters long[/]");
            AnsiConsole.WriteLine();
            continue;
        }

        string password2 = AnsiConsole.Prompt(
            new TextPrompt<string>("Confirm password:")
                .Secret());

        if (password1 != password2)
        {
            AnsiConsole.MarkupLine("[red]❌ Passwords do not match! Please try again.[/]");
            AnsiConsole.WriteLine();
            continue;
        }

        AnsiConsole.MarkupLine("[green]✓ Password confirmed and meets requirements[/]");
        return password1;
    }
}

void DisplaySuccessInfo(string childName, string configFile, string parentResource, string parentConfigFile)
{
    var successTable = new Table()
        .Border(TableBorder.Double)
        .Title("[bold green]🎉 Child Agent Created Successfully[/]")
        .AddColumn("[bold]Property[/]")
        .AddColumn("[bold]Value[/]");

    successTable.AddRow("👶 Child Agent", $"[cyan]{childName}[/]");
    successTable.AddRow("👨‍💼 Parent Resource", $"[blue]{parentResource}[/]");
    successTable.AddRow("📁 Parent Config", $"[yellow]{parentConfigFile}[/]");
    successTable.AddRow("📁 Child Config File", $"[green]{configFile}[/]");
    successTable.AddRow("🔐 Password", "[green]✓ Secured (32+ characters)[/]");
    successTable.AddRow("💬 Communication", "[yellow]Ready for message encryption/decryption[/]");
    successTable.AddRow("🔄 Load Command", $"[dim]dotnet script LoadChildAgent.csx -- {childName}[/]");

    AnsiConsole.Write(successTable);

    AnsiConsole.WriteLine();
    AnsiConsole.Write(
        new Panel(
            $"[green]✅ Child agent '{childName}' has been created successfully![/]\n\n" +
            $"[bold]Configuration:[/]\n" +
            $"• Parent config: [cyan]{parentConfigFile}[/]\n" +
            $"• Child config: [cyan]{configFile}[/]\n\n" +
            $"[bold]Next Steps:[/]\n" +
            $"• Use LoadChildAgent.csx to activate this child agent\n" +
            $"• Remember your password - it's required to load the agent\n" +
            $"• The child agent can now encrypt/decrypt messages within the same token server")
        .Header("🚀 Success!")
        .Border(BoxBorder.Double)
        .BorderColor(Color.Green));
}

// ====================================================================
// MAIN SCRIPT EXECUTION
// ====================================================================

DisplayHeader();

// Parse arguments
var (childName, showLogs, parentConfigFile) = ParseArguments(Args.ToArray());
if (string.IsNullOrEmpty(childName))
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

    // Check if parent agent exists
    if (!File.Exists(parentConfigFile))
    {
        AnsiConsole.MarkupLine($"[red]❌ Parent agent configuration not found: {parentConfigFile}[/]");
        AnsiConsole.MarkupLine("[yellow]💡 Please create a parent agent first using CreateParentAgent.csx[/]");
        AnsiConsole.WriteLine();
        AnsiConsole.MarkupLine($"[blue]Run:[/] dotnet script CreateParentAgent.csx -- {parentConfigFile}");
        return;
    }

    AnsiConsole.MarkupLine($"[green]✓[/] Parent agent configuration found: [cyan]{parentConfigFile}[/]");
    AnsiConsole.WriteLine();

    // Display child agent info
    DisplayChildAgentInfo(childName, parentConfigFile);

    // Generate child config filename
    string childConfigFile = $"child_{childName.ToLower().Replace(" ", "_").Replace("-", "_")}.json";

    // Check if child agent already exists
    if (File.Exists(childConfigFile))
    {
        bool overwrite = AnsiConsole.Confirm($"[yellow]⚠ Child agent '{childName}' already exists. Overwrite?[/]");
        if (!overwrite)
        {
            AnsiConsole.MarkupLine("[yellow]Operation cancelled.[/]");
            return;
        }
    }

    // Get and validate password
    string password = GetSecurePassword();
    if (string.IsNullOrEmpty(password))
    {
        AnsiConsole.MarkupLine("[red]❌ Password validation failed[/]");
        return;
    }

    // Create child agent
    bool success = false;
    AnsiConsole.Status()
        .Spinner(Spinner.Known.Star)
        .SpinnerStyle(Style.Parse("green"))
        .Start("Creating child agent...", ctx =>
        {
            ctx.Status("Initializing agent configuration...");
            var agentConfig = new AgentConfig();
            if (showLogs) agentConfig.EnableDebugMode();

            ctx.Status("Loading parent agent context...");
            Thread.Sleep(500);

            ctx.Status("Creating child agent identity...");
            success = agentConfig.CreateAIChildAgent(password, childConfigFile, true, clientId, tokenServerUrl, showLogs);
        });

    AnsiConsole.WriteLine();
    if (success)
    {
        DisplaySuccessInfo(childName, childConfigFile, resourceName, parentConfigFile);
    }
    else
    {
        AnsiConsole.Write(
            new Panel($"[red]✗ Failed to create child agent '{childName}'[/]\n" +
                     "[dim]Check your configuration and try again[/]")
            .Header("❌ Creation Failed")
            .Border(BoxBorder.Heavy)
            .BorderColor(Color.Red));

        AnsiConsole.WriteLine();
        AnsiConsole.MarkupLine("[yellow]💡 Troubleshooting tips:[/]");
        AnsiConsole.MarkupLine("• Ensure parent agent is properly created");
        AnsiConsole.MarkupLine("• Verify your env-file contains correct HexaEight credentials");
        AnsiConsole.MarkupLine("• Check network connectivity to the token server");
        AnsiConsole.MarkupLine("• Make sure the password meets the minimum requirements");
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
