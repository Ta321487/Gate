using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;

internal static class Program
{
    private static int Main(string[] args)
    {
        // AOCI UI polls this heavily; enumerating ~1e5 ignored paths under data/workspace
        // makes /api/state take ~30-60s. Index text does not depend on this listing.
        if (IsIgnoredOthersListing(args))
            return 0;

        string realGit = Environment.GetEnvironmentVariable("AOCI_REAL_GIT");
        if (string.IsNullOrWhiteSpace(realGit))
            realGit = @"D:\Program Files\Git\mingw64\bin\git.exe";

        var psi = new ProcessStartInfo
        {
            FileName = realGit,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = Environment.CurrentDirectory,
            StandardOutputEncoding = new UTF8Encoding(false),
            StandardErrorEncoding = new UTF8Encoding(false),
        };

        var sb = new StringBuilder();
        for (int i = 0; i < args.Length; i++)
        {
            if (i > 0) sb.Append(' ');
            sb.Append(QuoteArg(args[i]));
        }
        psi.Arguments = sb.ToString();

        try
        {
            using (var p = Process.Start(psi))
            {
                if (p == null) return 127;
                try { p.StandardInput.Close(); } catch { }

                Stream stdout = Console.OpenStandardOutput();
                Stream stderr = Console.OpenStandardError();
                Thread tOut = new Thread(() => CopyStream(p.StandardOutput.BaseStream, stdout));
                Thread tErr = new Thread(() => CopyStream(p.StandardError.BaseStream, stderr));
                tOut.IsBackground = true;
                tErr.IsBackground = true;
                tOut.Start();
                tErr.Start();

                p.WaitForExit();
                tOut.Join(120000);
                tErr.Join(120000);
                return p.ExitCode;
            }
        }
        catch (Exception ex)
        {
            try
            {
                byte[] msg = Encoding.UTF8.GetBytes("aoci-git-shim: " + ex.Message + Environment.NewLine);
                Console.OpenStandardError().Write(msg, 0, msg.Length);
            }
            catch { }
            return 127;
        }
    }

    private static bool IsIgnoredOthersListing(string[] args)
    {
        bool ls = false, others = false, ignored = false;
        for (int i = 0; i < args.Length; i++)
        {
            string a = args[i];
            if (a == "ls-files") ls = true;
            else if (a == "--others" || a == "-o") others = true;
            else if (a == "--ignored") ignored = true;
        }
        return ls && others && ignored;
    }

    private static void CopyStream(Stream input, Stream output)
    {
        try
        {
            byte[] buf = new byte[65536];
            int n;
            while ((n = input.Read(buf, 0, buf.Length)) > 0)
            {
                output.Write(buf, 0, n);
                output.Flush();
            }
        }
        catch { }
        try { output.Flush(); } catch { }
    }

    private static string QuoteArg(string arg)
    {
        if (arg.Length == 0) return "\"\"";
        bool needs = false;
        for (int i = 0; i < arg.Length; i++)
        {
            char c = arg[i];
            if (c == ' ' || c == '\t' || c == '"' || c == '\n' || c == '\v') { needs = true; break; }
        }
        if (!needs) return arg;

        var sb = new StringBuilder();
        sb.Append('"');
        int backslashes = 0;
        for (int i = 0; i < arg.Length; i++)
        {
            char c = arg[i];
            if (c == '\\') backslashes++;
            else if (c == '"')
            {
                sb.Append('\\', backslashes * 2 + 1);
                sb.Append('"');
                backslashes = 0;
            }
            else
            {
                if (backslashes > 0) { sb.Append('\\', backslashes); backslashes = 0; }
                sb.Append(c);
            }
        }
        if (backslashes > 0) sb.Append('\\', backslashes * 2);
        sb.Append('"');
        return sb.ToString();
    }
}
