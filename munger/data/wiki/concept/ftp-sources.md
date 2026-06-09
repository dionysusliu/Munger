>   There are

# FTP Sources

## Definition

**FTP Sources** refer to file repositories or servers that are accessible via the **File Transfer Protocol (FTP)**, a standard network protocol used to transfer files between a client and a server over a TCP/IP network. In the context of data acquisition, software development, and system administration, FTP sources are remote locations (typically URLs or host addresses) from which files—such as datasets, software packages, configuration files, or media—can be downloaded or uploaded.

FTP sources are often used in automated workflows, build systems, and data pipelines to retrieve or distribute files. They can be public (anonymous FTP) or require authentication (username/password). While FTP is older and less secure than modern alternatives like SFTP or HTTPS, it remains in use for legacy systems and certain specialized repositories.

## Examples

- **Public Software Repositories**: Many open-source projects historically hosted their releases on FTP servers (e.g., `ftp://ftp.gnu.org` for GNU software).
- **Data Archives**: Scientific datasets, such as climate or satellite imagery, are sometimes distributed via FTP (e.g., `ftp://ftp.ncdc.noaa.gov`).
- **Internal Corporate Servers**: Organizations may use FTP sources to share large files between departments or with external partners.
- **Package Managers**: Some package managers (e.g., older versions of `apt` or `yum`) could be configured to pull packages from FTP mirrors.
- **Web Hosting**: Users often upload website files to a server via FTP before the site goes live.

## Related Mental Models

- [[Client-Server Model]] – FTP operates on a client-server architecture where the client initiates a connection to the server to transfer files.
- [[Protocol Abstraction]] – FTP is one of many application-layer protocols; understanding it helps compare with HTTP, SFTP, SCP, etc.
- [[Legacy Systems]] – FTP sources are a classic example of technology that persists despite newer, more secure alternatives.
- [[Data Pipeline]] – FTP sources often serve as input stages in ETL (Extract, Transform, Load) processes.
- [[Authentication and Authorization]] – FTP sources can be public (anonymous) or require credentials, illustrating access control concepts.
- [[Network Ports]] – FTP uses port 21 for control and port 20 for data transfer, a model for understanding port-based services.

## See Also

- [[SFTP Sources]]
- [[HTTP Sources]]
- [[Data Ingestion]]
- [[File Transfer Protocol]]